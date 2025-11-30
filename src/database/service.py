"""
Database Service Layer
High-level functions for database operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import json

from .models import Bank, Category, Merchant, Transaction, TempUpload, UploadHistory


class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # REFERENCE DATA OPERATIONS
    # ============================================
    
    def get_or_create_bank(self, code: str, display_name: str = None, bank_type: str = None) -> Bank:
        """Get existing bank or create new one"""
        bank = self.db.query(Bank).filter(Bank.code == code).first()
        if not bank:
            bank = Bank(
                code=code,
                display_name=display_name or code,
                type=bank_type
            )
            self.db.add(bank)
            self.db.commit()
            self.db.refresh(bank)
        return bank
    
    def get_or_create_category(self, name: str, broad_category: str = None) -> Category:
        """Get existing category or create new one"""
        category = self.db.query(Category).filter(Category.name == name).first()
        if not category:
            category = Category(
                name=name,
                broad_category=broad_category
            )
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
        return category
    
    def get_or_create_merchant(self, name: str, category_id: int = None) -> Merchant:
        """Get existing merchant or create new one"""
        normalized = name.lower().strip()
        merchant = self.db.query(Merchant).filter(Merchant.normalized_name == normalized).first()
        if not merchant:
            merchant = Merchant(
                name=name,
                normalized_name=normalized,
                default_category_id=category_id
            )
            self.db.add(merchant)
            self.db.commit()
            self.db.refresh(merchant)
        return merchant
    
    # ============================================
    # TRANSACTION OPERATIONS
    # ============================================
    
    def add_transaction(self, txn_data: Dict[str, Any]) -> Optional[Transaction]:
        """
        Add a transaction to database
        Returns Transaction if added, None if duplicate
        """
        # Get or create foreign key references
        bank = self.get_or_create_bank(txn_data.get('bank', 'UNKNOWN'))
        category = self.get_or_create_category(txn_data.get('category', 'Uncategorized'))
        merchant = None
        if txn_data.get('merchant'):
            merchant = self.get_or_create_merchant(txn_data['merchant'], category.id)
        
        # Convert date string to date object if needed
        txn_date = txn_data['date']
        if isinstance(txn_date, str):
            # Handle both 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS' formats
            txn_date = txn_date.split()[0]  # Take only date part
            txn_date = datetime.strptime(txn_date, '%Y-%m-%d').date()
        
        # Create transaction
        transaction = Transaction(
            date=txn_date,
            amount=txn_data['amount'],
            description=txn_data.get('description'),
            type=txn_data['type'],
            bank_id=bank.id,
            category_id=category.id,
            merchant_id=merchant.id if merchant else None,
            account_number=txn_data.get('account_number'),
            balance=txn_data.get('balance'),
            cheque_no=txn_data.get('cheque_no'),
            value_date=txn_data.get('value_date'),
            source_file=txn_data.get('source_file'),
            reference=txn_data.get('reference'),
            year=txn_data.get('year'),
            raw_content=txn_data.get('raw_content')
        )
        
        try:
            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)
            return transaction
        except Exception as e:
            self.db.rollback()
            return None
    
    def bulk_add_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Add multiple transactions
        Returns: {saved: count, duplicates: count}
        """
        saved = 0
        duplicates = 0
        
        for txn_data in transactions:
            result = self.add_transaction(txn_data)
            if result:
                saved += 1
            else:
                duplicates += 1
        
        return {"saved": saved, "duplicates": duplicates}
    
    def get_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        bank_id: Optional[int] = None,
        txn_type: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Transaction]:
        """Get transactions with filters"""
        query = self.db.query(Transaction)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if bank_id:
            query = query.filter(Transaction.bank_id == bank_id)
        if txn_type:
            query = query.filter(Transaction.type == txn_type)
        
        return query.order_by(Transaction.date.desc()).limit(limit).offset(offset).all()
    
    # ============================================
    # TEMP UPLOAD OPERATIONS
    # ============================================
    
    def create_temp_upload(self, upload_id: str, filename: str, data: Dict[str, Any], hours: int = 24) -> TempUpload:
        """Create temporary upload record"""
        temp_upload = TempUpload(
            id=upload_id,
            filename=filename,
            uploaded_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=hours),
            transaction_count=len(data.get('transactions', [])),
            data=json.dumps(data)
        )
        self.db.add(temp_upload)
        self.db.commit()
        return temp_upload
    
    def get_temp_upload(self, upload_id: str) -> Optional[TempUpload]:
        """Get temporary upload by ID"""
        return self.db.query(TempUpload).filter(TempUpload.id == upload_id).first()
    
    def delete_temp_upload(self, upload_id: str):
        """Delete temporary upload"""
        self.db.query(TempUpload).filter(TempUpload.id == upload_id).delete()
        self.db.commit()
    
    def cleanup_expired_uploads(self):
        """Delete expired temporary uploads"""
        deleted = self.db.query(TempUpload).filter(
            TempUpload.expires_at < datetime.utcnow()
        ).delete()
        self.db.commit()
        return deleted
    
    # ============================================
    # ANALYTICS OPERATIONS
    # ============================================
    
    def get_summary_stats(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary statistics"""
        query = self.db.query(Transaction)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        # Calculate totals - use ABS for debits to ensure positive values
        debits = query.filter(Transaction.type == 'debit').with_entities(
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).first()
        
        credits = query.filter(Transaction.type == 'credit').with_entities(
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).first()
        
        return {
            "total_spent": float(debits.total or 0),
            "total_earned": float(credits.total or 0),
            "net_change": float(credits.total or 0) - float(debits.total or 0),
            "debit_count": debits.count or 0,
            "credit_count": credits.count or 0,
            "total_transactions": (debits.count or 0) + (credits.count or 0)
        }
    
    def get_category_summary(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get spending by category"""
        query = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).join(Transaction).filter(Transaction.type == 'debit')
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        results = query.group_by(Category.name).all()
        
        return [
            {"category": r.name, "total": float(r.total), "count": r.count}
            for r in results
        ]
