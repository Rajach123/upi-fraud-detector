import pandas as pd
import random

transactions = []

for i in range(1000):
    amount = random.randint(10, 50000)
    hour = random.randint(0, 23)
    is_fraud = 1 if (amount > 40000 and hour < 6) else 0
    transactions.append({
        "transaction_id": i + 1,
        "amount": amount,
        "hour": hour,
        "is_fraud": is_fraud
    })

df = pd.DataFrame(transactions)
df.to_csv("transactions.csv", index=False)
print("Done! transactions.csv created")
print(f"Total: {len(df)} transactions")
print(f"Fraud: {df['is_fraud'].sum()} transactions")