from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Tables ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="analyst")  # admin or analyst
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    hour = Column(Integer)
    sender_upi = Column(String)
    receiver_upi = Column(String)
    device_id = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    txn_velocity = Column(Integer)
    is_new_device = Column(Integer)
    is_fraud = Column(Boolean)
    risk_score = Column(Float)
    risk_level = Column(String)
    reasons = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    checked_by = Column(String, default="system")  # username

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
