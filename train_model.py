import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import pickle
import shap
import warnings
warnings.filterwarnings("ignore")

print("=" * 50)
print("Loading data...")
df = pd.read_csv("transactions.csv")
print(f"Total records: {len(df)} | Fraud: {df['is_fraud'].sum()}")

# --- Feature Engineering ---
print("\nEngineering features...")

# Encode UPI IDs as hash numbers (model can't use strings)
le_sender = LabelEncoder()
le_receiver = LabelEncoder()
le_device = LabelEncoder()

df["sender_enc"] = le_sender.fit_transform(df["sender_upi"])
df["receiver_enc"] = le_receiver.fit_transform(df["receiver_upi"])
df["device_enc"] = le_device.fit_transform(df["device_id"])

# Time-based features
df["is_night"] = ((df["hour"] >= 0) & (df["hour"] <= 5)).astype(int)
df["is_peak"] = ((df["hour"] >= 10) & (df["hour"] <= 18)).astype(int)

# Amount-based features
df["amount_log"] = np.log1p(df["amount"])
df["is_high_amount"] = (df["amount"] > 40000).astype(int)
df["is_medium_amount"] = ((df["amount"] > 10000) & (df["amount"] <= 40000)).astype(int)

# Risk combination features
df["night_high_amount"] = df["is_night"] * df["is_high_amount"]
df["new_device_high_amount"] = df["is_new_device"] * df["is_high_amount"]
df["velocity_risk"] = (df["txn_velocity"] >= 4).astype(int)

# Final feature list
FEATURES = [
    "amount", "hour", "amount_log",
    "is_night", "is_peak",
    "is_high_amount", "is_medium_amount",
    "txn_velocity", "is_new_device",
    "night_high_amount", "new_device_high_amount",
    "velocity_risk",
    "sender_enc", "receiver_enc", "device_enc",
    "latitude", "longitude"
]

X = df[FEATURES]
y = df["is_fraud"]

print(f"Features used: {len(FEATURES)}")
print(f"Feature list: {FEATURES}")

# --- Train / Test Split ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --- XGBoost Model ---
print("\nTraining XGBoost model...")

# Handle class imbalance
fraud_ratio = (y == 0).sum() / (y == 1).sum()

model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=fraud_ratio,  # handles imbalance
    random_state=42,
    eval_metric="logloss",
    verbosity=0
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

# --- Evaluation ---
print("\n" + "=" * 50)
print("MODEL EVALUATION")
print("=" * 50)

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Safe", "Fraud"]))

print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}")

# Cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print(f"Cross-Val AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"  True Negative  (Safe correctly): {cm[0][0]}")
print(f"  False Positive (Safe as Fraud) : {cm[0][1]}")
print(f"  False Negative (Fraud as Safe) : {cm[1][0]}")
print(f"  True Positive  (Fraud correctly): {cm[1][1]}")

# --- SHAP Feature Importance ---
print("\nCalculating SHAP values...")
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test[:100])  # sample for speed

# Top features
feature_importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print("\nTop 10 Important Features:")
print(feature_importance.head(10).to_string(index=False))

# --- Save everything ---
print("\nSaving model and artifacts...")

# Save model
with open("fraud_model.pkl", "wb") as f:
    pickle.dump(model, f)

# Save encoders (needed for API)
with open("encoders.pkl", "wb") as f:
    pickle.dump({
        "sender": le_sender,
        "receiver": le_receiver,
        "device": le_device
    }, f)

# Save feature list (needed for API)
with open("features.pkl", "wb") as f:
    pickle.dump(FEATURES, f)

# Save SHAP explainer
with open("shap_explainer.pkl", "wb") as f:
    pickle.dump(explainer, f)

print("\n" + "=" * 50)
print("Files saved:")
print("  fraud_model.pkl       — XGBoost model")
print("  encoders.pkl          — Label encoders")
print("  features.pkl          — Feature list")
print("  shap_explainer.pkl    — SHAP explainer")
print("=" * 50)
print("\nTraining complete!")
