from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pickle, numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings("ignore")

from database import get_db, create_tables, User, Transaction as TxnModel
from auth import (hash_password, verify_password, create_access_token,
                  get_current_user, require_admin)

app = FastAPI(title="UPI Fraud Detector API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Serve dashboard ---
@app.get("/dashboard")
def serve_dashboard():
    for name in ["dashboard_v5.html", "dashboard_v2.html", "dashboard (4).html", "dashboard.html"]:
        if os.path.exists(name):
            return FileResponse(name, media_type="text/html")
    return {"error": "Dashboard not found"}

# --- Load ML artifacts ---
print("Loading model...")
with open("fraud_model.pkl", "rb") as f:
    model = pickle.load(f)
with open("encoders.pkl", "rb") as f:
    encoders = pickle.load(f)
with open("features.pkl", "rb") as f:
    FEATURES = pickle.load(f)
with open("shap_explainer.pkl", "rb") as f:
    explainer = pickle.load(f)
print("Model loaded!")

@app.on_event("startup")
def startup():
    create_tables()
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin", email="admin@upifraud.com",
                hashed_password=hash_password("Admin@123"), role="admin"
            )
            db.add(admin_user); db.commit()
            print("Default admin created: username=admin password=Admin@123")
    finally:
        db.close()

class TransactionInput(BaseModel):
    amount: float
    hour: int
    sender_upi: str = "user@oksbi"
    receiver_upi: str = "merchant@ybl"
    device_id: str = "device_abc123"
    latitude: float = 17.38
    longitude: float = 78.48
    txn_velocity: int = 1
    is_new_device: int = 0

class RegisterInput(BaseModel):
    username: str
    email: str
    password: str
    role: str = "analyst"

def safe_encode(encoder, value):
    try:
        return int(encoder.transform([value])[0])
    except:
        return -1

def build_features(t: TransactionInput) -> pd.DataFrame:
    amount_log = np.log1p(t.amount)
    is_night = 1 if 0 <= t.hour <= 5 else 0
    is_peak = 1 if 10 <= t.hour <= 18 else 0
    is_high = 1 if t.amount > 40000 else 0
    is_mid = 1 if 10000 < t.amount <= 40000 else 0
    row = {
        "amount": t.amount, "hour": t.hour, "amount_log": amount_log,
        "is_night": is_night, "is_peak": is_peak,
        "is_high_amount": is_high, "is_medium_amount": is_mid,
        "txn_velocity": t.txn_velocity, "is_new_device": t.is_new_device,
        "night_high_amount": is_night * is_high,
        "new_device_high_amount": t.is_new_device * is_high,
        "velocity_risk": 1 if t.txn_velocity >= 4 else 0,
        "sender_enc": safe_encode(encoders["sender"], t.sender_upi),
        "receiver_enc": safe_encode(encoders["receiver"], t.receiver_upi),
        "device_enc": safe_encode(encoders["device"], t.device_id),
        "latitude": t.latitude, "longitude": t.longitude,
    }
    return pd.DataFrame([row])[FEATURES]

@app.post("/auth/register")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=data.username, email=data.email,
                hashed_password=hash_password(data.password), role=data.role)
    db.add(user); db.commit()
    return {"message": f"User '{data.username}' registered!", "role": data.role}

@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer",
            "username": user.username, "role": user.role}

@app.get("/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email, "role": current_user.role}

@app.post("/predict")
def predict(transaction: TransactionInput, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    try:
        X = build_features(transaction)
        prediction = int(model.predict(X)[0])
        probability = float(model.predict_proba(X)[0][1])
        risk_score = round(probability * 100, 1)
        shap_vals = explainer.shap_values(X)[0]
        feature_impacts = dict(zip(FEATURES, [round(float(v), 4) for v in shap_vals]))
        sorted_impacts = sorted(feature_impacts.items(), key=lambda x: abs(x[1]), reverse=True)
        reason_map = {
            "is_night": "Late night transaction (12AM–5AM)",
            "is_high_amount": "High amount (>₹40,000)",
            "night_high_amount": "High amount during late night",
            "txn_velocity": "Multiple rapid transactions",
            "velocity_risk": "High transaction velocity",
            "is_new_device": "New/unknown device",
            "new_device_high_amount": "High amount from new device",
            "amount": "Unusual transaction amount",
            "device_enc": "Unrecognized device",
            "sender_enc": "Unrecognized sender UPI",
        }
        reasons = []
        for feat, impact in sorted_impacts[:5]:
            if abs(impact) > 0.01 and feat in reason_map:
                reasons.append(reason_map[feat])
            if len(reasons) == 3:
                break
        risk_level = "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW"
        txn = TxnModel(
            amount=transaction.amount, hour=transaction.hour,
            sender_upi=transaction.sender_upi, receiver_upi=transaction.receiver_upi,
            device_id=transaction.device_id, latitude=transaction.latitude,
            longitude=transaction.longitude, txn_velocity=transaction.txn_velocity,
            is_new_device=transaction.is_new_device, is_fraud=bool(prediction),
            risk_score=risk_score, risk_level=risk_level,
            reasons=json.dumps(reasons), checked_by=current_user.username
        )
        db.add(txn); db.commit()
        return {
            "amount": transaction.amount, "hour": transaction.hour,
            "sender_upi": transaction.sender_upi, "is_fraud": bool(prediction),
            "risk_score": risk_score, "risk_level": risk_level,
            "fraud_probability": round(probability, 4),
            "reasons": reasons if prediction else [],
            "message": "🚨 FRAUD DETECTED!" if prediction else "✅ Transaction is Safe",
            "saved_to_db": True, "checked_by": current_user.username
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def history(limit: int = 50, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    txns = db.query(TxnModel).order_by(TxnModel.created_at.desc()).limit(limit).all()
    return [{"id": t.id, "amount": t.amount, "hour": t.hour,
             "sender_upi": t.sender_upi, "is_fraud": t.is_fraud,
             "risk_score": t.risk_score, "risk_level": t.risk_level,
             "reasons": json.loads(t.reasons) if t.reasons else [],
             "checked_by": t.checked_by,
             "time": t.created_at.strftime("%Y-%m-%d %H:%M:%S")} for t in txns]

@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), admin=Depends(require_admin)):
    total = db.query(TxnModel).count()
    fraud = db.query(TxnModel).filter(TxnModel.is_fraud == True).count()
    return {"total_transactions": total, "total_fraud": fraud,
            "fraud_rate": round(fraud/total*100, 1) if total > 0 else 0,
            "total_users": db.query(User).count()}

@app.get("/")
def home():
    return {"message": "UPI Fraud Detector API v3.0 — Go to /dashboard"}