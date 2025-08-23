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
    total_earned: float = Field(..., description="Total amount earned")
    total_spent: float = Field(..., description="Total amount spent")
    net_change: float = Field(..., description="Net portfolio change")
    total_transactions: int = Field(..., description="Total number of transactions")
    date_range_start: str = Field(..., description="Start date of data range")
    date_range_end: str = Field(..., description="End date of data range")

# ============================================================================
# NEW MODELS FOR MISSING SECTIONS
# ============================================================================

class AccountBalance(BaseModel):
    """Account balance model"""
    account_type: str = Field(..., description="Account type (checking, savings, etc.)")
    balance: float = Field(0.0, description="Current balance")
    account_name: str = Field(..., description="Account display name")

class MonthlyTrendItem(BaseModel):
    """Monthly trend data point"""
    month: str = Field(..., description="Month name (Jan, Feb, etc.)")
    income: float = Field(0.0, description="Monthly income")
    expenses: float = Field(0.0, description="Monthly expenses")
    savings: float = Field(0.0, description="Monthly savings")

class BudgetProgressItem(BaseModel):
    """Budget progress for a category"""
    category: str = Field(..., description="Category name")
    spent: float = Field(0.0, description="Amount spent")
    budget: float = Field(0.0, description="Budget amount")
    percentage: float = Field(0.0, description="Percentage of budget used")

class UpcomingBill(BaseModel):
    """Upcoming bill item"""
    name: str = Field(..., description="Bill name")
    amount: float = Field(0.0, description="Bill amount")
    due_date: str = Field(..., description="Due date (YYYY-MM-DD)")
    status: str = Field("pending", description="Bill status")

# ============================================================================
# RESPONSE MODELS FOR NEW ENDPOINTS
# ============================================================================

class AccountBalancesResponse(BaseModel):
    """Response model for account balances"""
    accounts: List[AccountBalance] = Field(..., description="List of account balances")
    total_balance: float = Field(0.0, description="Total balance across all accounts")

class MonthlyTrendResponse(BaseModel):
    """Response model for monthly trend data"""
    monthly_data: List[MonthlyTrendItem] = Field(..., description="Monthly trend data")
    period_months: int = Field(6, description="Number of months in the trend")

class BudgetProgressResponse(BaseModel):
    """Response model for budget progress"""
    budget_items: List[BudgetProgressItem] = Field(..., description="Budget progress items")
    total_budget: float = Field(0.0, description="Total budget amount")
    total_spent: float = Field(0.0, description="Total amount spent")

class UpcomingBillsResponse(BaseModel):
    """Response model for upcoming bills"""
    bills: List[UpcomingBill] = Field(..., description="List of upcoming bills")
    total_amount: float = Field(0.0, description="Total amount of upcoming bills")

# ============================================================================
# EXISTING RESPONSE MODELS
# ============================================================================

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
