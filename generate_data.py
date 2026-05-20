import pandas as pd
import numpy as np
import random
import hashlib

random.seed(42)
np.random.seed(42)

# --- Helpers ---
def fake_upi_id():
    users = ["rajesh", "priya", "suresh", "anita", "kumar", "lakshmi", "venkat", "deepa"]
    banks = ["oksbi", "okaxis", "ybl", "ibl", "paytm", "apl"]
    return f"{random.choice(users)}{random.randint(1,999)}@{random.choice(banks)}"

def fake_device_id():
    return hashlib.md5(str(random.randint(100000, 999999)).encode()).hexdigest()[:12]

def fake_location():
    # Indian cities with lat/lng
    cities = [
        (17.38, 78.48),   # Hyderabad
        (13.08, 80.27),   # Chennai
        (12.97, 77.59),   # Bangalore
        (19.07, 72.87),   # Mumbai
        (28.70, 77.10),   # Delhi
        (22.57, 88.36),   # Kolkata
        (23.02, 72.57),   # Ahmedabad
        (18.52, 73.85),   # Pune
    ]
    base = random.choice(cities)
    # Add small random offset
    return round(base[0] + random.uniform(-0.5, 0.5), 4), round(base[1] + random.uniform(-0.5, 0.5), 4)

transactions = []

# Pre-assign some "known fraudster" UPI IDs and devices
fraud_upi_ids = [fake_upi_id() for _ in range(20)]
fraud_devices = [fake_device_id() for _ in range(15)]

for i in range(5000):
    amount = int(np.random.exponential(scale=8000)) + 100
    amount = min(amount, 100000)

    probs = [0.06,0.05,0.04,0.03,0.02,0.02,
             0.03,0.05,0.07,0.08,0.07,0.06,
             0.07,0.07,0.06,0.05,0.05,0.05,
             0.05,0.04,0.04,0.03,0.03,0.04]
    probs = np.array(probs)
    probs = probs / probs.sum()  # normalize to exactly 1.0
    hour = int(np.random.choice(range(24), p=probs))

    sender_upi = fake_upi_id()
    receiver_upi = fake_upi_id()
    device_id = fake_device_id()
    lat, lng = fake_location()

    # Transaction velocity: how many txns in last hour (simulated)
    txn_velocity = random.randint(1, 5)

    # Is new device? (0 or 1)
    is_new_device = random.choice([0, 0, 0, 1])  # 25% new devices

    # --- Fraud Logic (realistic patterns) ---
    fraud_score = 0

    # Pattern 1: High amount at odd hours
    if amount > 40000 and hour < 6:
        fraud_score += 40

    # Pattern 2: Known fraudster UPI ID
    if sender_upi in fraud_upi_ids:
        fraud_score += 35

    # Pattern 3: Known fraudster device
    if device_id in fraud_devices:
        fraud_score += 30

    # Pattern 4: High velocity (many transactions quickly)
    if txn_velocity >= 4:
        fraud_score += 20

    # Pattern 5: New device + high amount
    if is_new_device and amount > 20000:
        fraud_score += 25

    # Pattern 6: Very late night + new device
    if hour <= 3 and is_new_device:
        fraud_score += 20

    # Add randomness
    fraud_score += random.randint(-10, 10)

    is_fraud = 1 if fraud_score >= 50 else 0

    transactions.append({
        "transaction_id": i + 1,
        "amount": amount,
        "hour": hour,
        "sender_upi": sender_upi,
        "receiver_upi": receiver_upi,
        "device_id": device_id,
        "latitude": lat,
        "longitude": lng,
        "txn_velocity": txn_velocity,
        "is_new_device": is_new_device,
        "is_fraud": is_fraud
    })

df = pd.DataFrame(transactions)
df.to_csv("transactions.csv", index=False)

print("=" * 50)
print("transactions.csv created!")
print(f"Total transactions : {len(df)}")
print(f"Fraud transactions : {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")
print(f"Safe transactions  : {(df['is_fraud']==0).sum()}")
print("=" * 50)
print("\nSample fraud transaction:")
print(df[df['is_fraud']==1].head(1).to_string())