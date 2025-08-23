"""
API Models for FinanceAnalyzer
Pydantic models for request/response validation and documentation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# ============================================================================
# REQUEST MODELS
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request model for file analysis"""
    from_date: Optional[str] = Field(None, description="Start date filter (MM-YYYY)")
    to_date: Optional[str] = Field(None, description="End date filter (MM-YYYY)")
    portfolio_mode: Optional[bool] = Field(False, description="Enable portfolio analysis mode")

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    message: str = "FinanceAnalyzer API is running"
    version: str = "1.0.0"

class AnalyzeResponse(BaseModel):
    """File analysis response"""
    analysis_id: str
    files_processed: int
    file_names: List[str]
    status: str = "completed"

class OverallSummary(BaseModel):
    """Overall financial summary data"""
    total_spends_debits: float = Field(alias="Total Spends (Debits)")
    total_credits: float = Field(alias="Total Credits")
    net_change: float = Field(alias="Net Change")
    total_transactions: int = Field(alias="Total Transactions")

    class Config:
        populate_by_name = True

class CategoryItem(BaseModel):
    """Category item for spending/earning breakdown"""
    Category: str
    Total_Debit: Optional[float] = Field(None, alias="Total Debit")
    Debit_Count: Optional[int] = Field(None, alias="Debit Count")
    Total_Credit: Optional[float] = Field(None, alias="Total Credit")
    Credit_Count: Optional[int] = Field(None, alias="Credit Count")

    class Config:
        populate_by_name = True

class DateRange(BaseModel):
    """Date range information"""
    start_date: Optional[str]
    end_date: Optional[str]

class FilterInfo(BaseModel):
    """Filter information"""
    applied: str = "All Data"

class OverallSummaryResponse(BaseModel):
    """Overall summary endpoint response"""
    analysis_id: str
    overall_summary: OverallSummary
    top_spending_categories: List[CategoryItem]
    top_earning_categories: List[CategoryItem]
    top_categories: List[CategoryItem]  # For frontend compatibility
    date_range: DateRange
    filter_info: FilterInfo

class CategorySummaryItem(BaseModel):
    """Detailed category summary item"""
    Category: str
    Total_Debit: float = Field(alias="Total Debit")
    Debit_Count: int = Field(alias="Debit Count")
    Total_Credit: float = Field(alias="Total Credit")
    Credit_Count: int = Field(alias="Credit Count")
    Net_Amount: float = Field(alias="Net Amount")
    Transaction_Type: str = Field(alias="Transaction Type")

    class Config:
        populate_by_name = True

class CategorySummaryData(BaseModel):
    """Category summary data wrapper"""
    category_summary: List[CategorySummaryItem]

class CategorySummaryResponse(BaseModel):
    """Category summary endpoint response"""
    analysis_id: str
    category_summary: CategorySummaryData

class PortfolioSummary(BaseModel):
    """Portfolio analysis summary"""
    total_transactions: int
    external_transactions: int
    self_transfers_ignored: int
    external_inflows: float
    external_outflows: float
    net_portfolio_change: float

class FlowBreakdownItem(BaseModel):
    """Portfolio flow breakdown item"""
    category: str
    amount: float
    count: int
    percentage: float

class PortfolioInsights(BaseModel):
    """Portfolio analysis insights"""
    summary: PortfolioSummary
    external_inflows_breakdown: List[FlowBreakdownItem]
    external_outflows_breakdown: List[FlowBreakdownItem]
    analysis_type: str = "portfolio"
    note: str

class PortfolioResponse(BaseModel):
    """Portfolio analysis endpoint response"""
    analysis_id: str
    portfolio_insights: PortfolioInsights

class UPISummary(BaseModel):
    """UPI analysis summary"""
    total_upi_transactions: int
    total_upi_debit: float
    total_upi_credit: float
    net_upi_amount: float

class UPICategoryItem(BaseModel):
    """UPI category item"""
    category: str
    total_debit: float
    debit_count: int
    total_credit: float
    credit_count: int
    net_amount: float

class UPISubcategory(BaseModel):
    """UPI subcategory data"""
    debit: float
    credit: float
    count: int

class UPIHierarchyItem(BaseModel):
    """UPI hierarchy main category"""
    total_debit: float
    total_credit: float
    net_amount: float
    subcategories: Dict[str, UPISubcategory]

class UPIAnalysisData(BaseModel):
    """UPI analysis data"""
    summary: UPISummary
    upi_spending_categories: List[UPICategoryItem]
    upi_hierarchy: Dict[str, UPIHierarchyItem]

class UPIResponse(BaseModel):
    """UPI analysis endpoint response"""
    analysis_id: str
    upi_analysis: UPIAnalysisData

class Transaction(BaseModel):
    """Transaction item"""
    Date: str
    Description: str
    Amount: float
    Category: str
    Reference: str
    Balance: float
    Debit: float
    Credit: float
    Transaction_Type: str
    Source_File: str
    Bank: str
    Year: int
    Broad_Category: Optional[str] = None

class TransactionSummary(BaseModel):
    """Transaction list summary"""
    total_debits_shown: float
    total_credits_shown: float
    net_amount_shown: float

class TransactionsResponse(BaseModel):
    """Transactions endpoint response"""
    analysis_id: str
    transactions: List[Transaction]
    total_shown: int
    summary: TransactionSummary
    note: str

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
