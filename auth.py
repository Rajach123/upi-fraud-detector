from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("fraud_model.pkl", "rb") as f:
    model = pickle.load(f)

class Transaction(BaseModel):
    amount: int
    hour: int

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/")
def home():
    return {"message": "UPI Fraud Detector API is running!"}

@app.post("/auth/login")
def login(req: LoginRequest):
    if req.username == "admin" and req.password == "Admin@123":
        return {"access_token": "admin-token-123", "token_type": "bearer"}
    return {"error": "Invalid credentials"}

@app.post("/predict")
def predict(transaction: Transaction):
    result = model.predict([[transaction.amount, transaction.hour]])
    fraud = bool(result[0])
    return {
        "amount": transaction.amount,
        "hour": transaction.hour,
        "is_fraud": fraud,
        "message": "🚨 FRAUD DETECTED!" if fraud else "✅ Transaction is Safe"
    }