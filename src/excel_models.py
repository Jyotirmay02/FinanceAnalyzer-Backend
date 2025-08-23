

from pydantic import BaseModel
from typing import List

class PortfolioOverallSummaryData(BaseModel):
    """
    A model representing financial portfolio data with earnings, spending,
    transactions, and date ranges.
    """
    # Core financial metrics
    total_earned: float
    total_spent: float
    net_portfolio_change: float

    # Transaction counts
    total_transactions: int
    external_transactions: int
    self_transfer_transactions: int
    external_outflows: int
    external_inflows: float
    net_portfolio_change_transactions: float
    self_transfers_ignored: int

    # Date ranges
    data_range_start: str
    data_range_end: str
    report_generation_time: str


class PortfolioCategorySummaryItem(BaseModel):
    """
    A model representing a summary of transactions for a specific category.
    """
    category: str
    total_debit: float
    debit_count: int
    total_credit: float
    credit_count: int
    net_amount: float

class PortfolioUpiAnalysisItem(BaseModel):
    """
    A model representing a summary of UPI transactions for a specific category.
    """
    category: str
    total_debit: float
    debit_count: int
    total_credit: float
    credit_count: int
    net_amount: float

class PortfolioUpiSummary(BaseModel):
    """
    A model representing the overall summary of UPI transactions.
    """
    category: str
    total_amount: float

class PortfolioCategorizedTransactionItem(BaseModel):
    """
    A model representing a categorized transaction.
    """
    txn_date: str
    value_date: str
    cheque_no: str
    description: str
    debit_amount: float
    credit_amount: float
    balance_amount: float
    category: str
    source_file: str
    bank: str
    reference: str
    year: int
    broad_category: str


class PortfolioAnalysisData(BaseModel):
    """
    A model representing the overall portfolio analysis data.
    """
    overall_summary: PortfolioOverallSummaryData
    categorized_transactions: List[PortfolioCategorizedTransactionItem]
    category_summary: List[PortfolioCategorySummaryItem]
    upi_summary: List[PortfolioUpiSummary]
    upi_analysis: List[PortfolioUpiAnalysisItem]