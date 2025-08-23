"""
API v2 Models for FinanceAnalyzer - Mint-like Frontend
Pydantic models for v2 endpoints with proper typing and validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class ViewType(str, Enum):
    SPENDING = "spending"
    INCOME = "income"

# ============================================================================
# CORE DATA MODELS
# ============================================================================

class CategorySummaryV2(BaseModel):
    """Category summary for v2 API"""
    category: str = Field(..., description="Category name")
    total_debit: float = Field(0.0, description="Total debit amount")
    debit_count: int = Field(0, description="Number of debit transactions")
    total_credit: float = Field(0.0, description="Total credit amount") 
    credit_count: int = Field(0, description="Number of credit transactions")
    net_amount: float = Field(..., description="Net amount (credit - debit)")
    percentage: float = Field(..., description="Percentage of total")

class TransactionV2(BaseModel):
    """Transaction model for v2 API"""
    id: str = Field(..., description="Unique transaction identifier")
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount (positive for credit, negative for debit)")
    category: str = Field(..., description="Transaction category")
    bank: str = Field(..., description="Bank name")
    balance: float = Field(..., description="Account balance after transaction")
    transaction_type: TransactionType = Field(..., description="Transaction type")
    source_file: str = Field(..., description="Source file name")

class OverallSummaryV2(BaseModel):
    """Overall summary for v2 API"""
    total_earned: float = Field(..., description="Total income/credits")
    total_spent: float = Field(..., description="Total expenses/debits") 
    net_change: float = Field(..., description="Net portfolio change")
    total_transactions: int = Field(..., description="Total number of transactions")
    date_range_start: str = Field(..., description="Analysis start date")
    date_range_end: str = Field(..., description="Analysis end date")

class UPICategoryV2(BaseModel):
    """UPI category for v2 API"""
    category: str = Field(..., description="UPI category name")
    total_debit: float = Field(0.0, description="Total UPI debit amount")
    debit_count: int = Field(0, description="Number of UPI debit transactions")
    total_credit: float = Field(0.0, description="Total UPI credit amount")
    credit_count: int = Field(0, description="Number of UPI credit transactions")
    net_amount: float = Field(..., description="Net UPI amount")
    percentage: float = Field(..., description="Percentage of total UPI")

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class DashboardResponse(BaseModel):
    """Dashboard data response"""
    overall_summary: OverallSummaryV2
    top_spending_categories: List[CategorySummaryV2] = Field(..., max_items=5)
    top_income_categories: List[CategorySummaryV2] = Field(..., max_items=5)
    recent_transactions: List[TransactionV2] = Field(..., max_items=10)

class CategoriesResponse(BaseModel):
    """Categories page response"""
    spending_categories: List[CategorySummaryV2]
    income_categories: List[CategorySummaryV2]
    total_spending: float
    total_income: float

class TransactionsResponse(BaseModel):
    """Transactions page response"""
    transactions: List[TransactionV2]
    total_count: int
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)
    total_pages: int
    summary: OverallSummaryV2

class UPIAnalysisResponse(BaseModel):
    """UPI Analysis page response"""
    upi_categories: List[UPICategoryV2]
    total_upi_debit: float
    total_upi_credit: float
    total_upi_transactions: int
    net_upi_amount: float

# ============================================================================
# REQUEST MODELS
# ============================================================================

class PaginationRequest(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")

class TransactionFilters(BaseModel):
    """Transaction filtering parameters"""
    category: Optional[str] = Field(None, description="Filter by category")
    transaction_type: Optional[TransactionType] = Field(None, description="Filter by transaction type")
    date_from: Optional[str] = Field(None, description="Start date filter (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date filter (YYYY-MM-DD)")
    search: Optional[str] = Field(None, description="Search in description")

class CategoryFilters(BaseModel):
    """Category filtering parameters"""
    view_type: ViewType = Field(ViewType.SPENDING, description="View spending or income categories")
    min_amount: Optional[float] = Field(None, description="Minimum amount filter")

# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorResponseV2(BaseModel):
    """Standard error response for v2"""
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict] = Field(None, description="Additional error details")
