from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class BaseTransaction:
    """Base transaction model"""
    amount: float
    date: str
    bank: str
    transaction_type: str  # credit/debit
    metadata: Dict[str, Any]

@dataclass
class CardTransaction(BaseTransaction):
    """Credit/Debit card transaction model"""
    merchant: str
    card_last4: str
    time: Optional[str] = None
    category: Optional[str] = None
    reference_number: Optional[str] = None
    
    def __post_init__(self):
        self.metadata['transaction_category'] = 'card'

@dataclass
class AccountTransferTransaction(BaseTransaction):
    """Bank account transfer (IMPS/NEFT/RTGS) model"""
    transfer_type: str  # IMPS/NEFT/RTGS
    beneficiary_name: Optional[str] = None
    beneficiary_account: Optional[str] = None
    sender_name: Optional[str] = None
    sender_account: Optional[str] = None
    reference_number: Optional[str] = None
    remarks: Optional[str] = None
    
    def __post_init__(self):
        self.metadata['transaction_category'] = 'transfer'

@dataclass
class SalaryTransaction(BaseTransaction):
    """Salary/automated credit transaction model"""
    employer_name: str
    payment_type: str  # NACH/ECS/Direct Credit
    employee_id: Optional[str] = None
    reference_number: Optional[str] = None
    
    def __post_init__(self):
        self.metadata['transaction_category'] = 'salary'

@dataclass
class RefundTransaction(BaseTransaction):
    """Refund/adjustment transaction model"""
    original_merchant: Optional[str] = None
    adjustment_type: str = 'refund'  # refund/adjustment/cashback
    reference_number: Optional[str] = None
    
    def __post_init__(self):
        self.metadata['transaction_category'] = 'refund'

class TransactionFactory:
    """Factory to create appropriate transaction models"""
    
    @staticmethod
    def create_transaction(raw_data: Dict) -> BaseTransaction:
        """Create appropriate transaction model based on data"""
        
        # Determine transaction category
        if raw_data.get('card_last4'):
            return TransactionFactory._create_card_transaction(raw_data)
        elif 'IMPS' in raw_data.get('merchant', '').upper():
            return TransactionFactory._create_transfer_transaction(raw_data)
        elif 'NACH' in raw_data.get('merchant', '').upper() or 'ECS' in raw_data.get('merchant', '').upper():
            return TransactionFactory._create_salary_transaction(raw_data)
        elif raw_data.get('transaction_type') == 'credit' and 'adjustment' in raw_data.get('merchant', '').lower():
            return TransactionFactory._create_refund_transaction(raw_data)
        else:
            # Default to card transaction
            return TransactionFactory._create_card_transaction(raw_data)
    
    @staticmethod
    def _create_card_transaction(data: Dict) -> CardTransaction:
        """Create card transaction model"""
        return CardTransaction(
            amount=data['amount'],
            date=data['date'],
            bank=data['bank'],
            transaction_type=data['transaction_type'],
            merchant=data['merchant'],
            card_last4=data.get('card_last4', ''),
            time=data.get('time'),
            reference_number=data.get('reference_number'),
            metadata=data.get('metadata', {})
        )
    
    @staticmethod
    def _create_transfer_transaction(data: Dict) -> AccountTransferTransaction:
        """Create transfer transaction model"""
        merchant = data.get('merchant', '')
        
        # Extract transfer details
        transfer_type = 'IMPS'  # Default
        beneficiary_name = None
        sender_name = None
        
        if 'IMPS to' in merchant:
            beneficiary_name = merchant.replace('IMPS to ', '').strip()
        elif 'IMPS from' in merchant:
            sender_name = merchant.replace('IMPS from ', '').strip()
        
        return AccountTransferTransaction(
            amount=data['amount'],
            date=data['date'],
            bank=data['bank'],
            transaction_type=data['transaction_type'],
            transfer_type=transfer_type,
            beneficiary_name=beneficiary_name,
            sender_name=sender_name,
            reference_number=data.get('reference_number'),
            metadata=data.get('metadata', {})
        )
    
    @staticmethod
    def _create_salary_transaction(data: Dict) -> SalaryTransaction:
        """Create salary transaction model"""
        merchant = data.get('merchant', '')
        
        # Extract employer name
        employer_name = merchant
        payment_type = 'NACH'
        
        if 'NACH/ECS from' in merchant:
            employer_name = merchant.replace('NACH/ECS from ', '').strip()
            payment_type = 'NACH/ECS'
        elif 'AMAZON' in merchant.upper():
            employer_name = 'Amazon Development Centre India Private Limited'
            payment_type = 'IMPS'
        
        return SalaryTransaction(
            amount=data['amount'],
            date=data['date'],
            bank=data['bank'],
            transaction_type=data['transaction_type'],
            employer_name=employer_name,
            payment_type=payment_type,
            reference_number=data.get('reference_number'),
            metadata=data.get('metadata', {})
        )
    
    @staticmethod
    def _create_refund_transaction(data: Dict) -> RefundTransaction:
        """Create refund transaction model"""
        return RefundTransaction(
            amount=data['amount'],
            date=data['date'],
            bank=data['bank'],
            transaction_type=data['transaction_type'],
            adjustment_type='credit_adjustment',
            reference_number=data.get('reference_number'),
            metadata=data.get('metadata', {})
        )

def transaction_to_dict(transaction: BaseTransaction) -> Dict:
    """Convert transaction model to dictionary"""
    return asdict(transaction)
