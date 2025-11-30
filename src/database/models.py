"""
Database Models for FinanceAnalyzer
SQLAlchemy ORM models for normalized transaction storage
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Bank(Base):
    """Reference table for banks/financial institutions"""
    __tablename__ = 'banks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)  # ICICI_CC, HDFC_SAV
    display_name = Column(String(100), nullable=False)
    type = Column(String(20))  # credit_card, savings, wallet
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="bank")


class Category(Base):
    """Reference table for transaction categories"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    broad_category = Column(String(50))  # Expenses, Income, Transfer
    icon = Column(String(10))  # Emoji icon
    color = Column(String(7))  # Hex color code
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="category")
    merchants = relationship("Merchant", back_populates="default_category")


class Merchant(Base):
    """Reference table for merchants/payees"""
    __tablename__ = 'merchants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    normalized_name = Column(String(200))  # Lowercase, no special chars
    default_category_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    default_category = relationship("Category", back_populates="merchants")
    transactions = relationship("Transaction", back_populates="merchant")


class Transaction(Base):
    """Main transaction table - normalized storage"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core transaction data
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    type = Column(String(10), nullable=False)  # debit, credit
    
    # Foreign keys (normalized references)
    bank_id = Column(Integer, ForeignKey('banks.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    merchant_id = Column(Integer, ForeignKey('merchants.id'))
    
    # Banking details
    account_number = Column(String(50))
    balance = Column(Float)
    cheque_no = Column(String(50))
    value_date = Column(Date)
    
    # Metadata
    source_file = Column(String(255))
    reference = Column(String(100))
    year = Column(Integer)
    raw_content = Column(Text)  # Original email/SMS content
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bank = relationship("Bank", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_date', 'date'),
        Index('idx_category', 'category_id'),
        Index('idx_merchant', 'merchant_id'),
        Index('idx_bank', 'bank_id'),
        Index('idx_type', 'type'),
        Index('idx_year', 'year'),
        # Deduplication constraint
        UniqueConstraint('date', 'amount', 'description', 'bank_id', name='uq_transaction'),
    )


class TempUpload(Base):
    """Temporary storage for uploads before user saves"""
    __tablename__ = 'temp_uploads'
    
    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    transaction_count = Column(Integer)
    data = Column(Text)  # JSON string of full analysis
    
    __table_args__ = (
        Index('idx_expires', 'expires_at'),
    )


class UploadHistory(Base):
    """Track upload history and save decisions"""
    __tablename__ = 'upload_history'
    
    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    saved_at = Column(DateTime)
    new_transactions = Column(Integer)
    duplicate_transactions = Column(Integer)
    status = Column(String(20))  # preview, saved, discarded
    
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_uploaded_at', 'uploaded_at'),
    )
