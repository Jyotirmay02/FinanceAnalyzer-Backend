"""
API v2 Transformers for FinanceAnalyzer
Transform backend data models to v2 API response models
"""

from typing import List, Dict, Any
import uuid
from datetime import datetime

from .api_v2_models import *
from .excel_models import *

class APIv2Transformer:
    """Transform backend data to v2 API models"""
    
    @staticmethod
    def transform_overall_summary(data: PortfolioOverallSummaryData) -> OverallSummaryV2:
        """Transform overall summary data"""
        return OverallSummaryV2(
            total_earned=data.total_earned,
            total_spent=data.total_spent,
            net_change=data.net_portfolio_change,  # Use correct field name
            total_transactions=data.total_transactions,
            date_range_start=data.data_range_start,
            date_range_end=data.data_range_end
        )
    
    @staticmethod
    def transform_category_summary(categories: List[PortfolioCategorySummaryItem]) -> tuple[List[CategorySummaryV2], List[CategorySummaryV2]]:
        """Transform category data into spending and income categories"""
        spending_categories = []
        income_categories = []
        
        # Calculate totals for percentage calculation
        total_spending = sum(abs(cat.total_debit) for cat in categories if cat.total_debit > 0)
        total_income = sum(cat.total_credit for cat in categories if cat.total_credit > 0)
        
        for cat in categories:
            # Spending categories (categories with debits)
            if cat.total_debit > 0:
                spending_categories.append(CategorySummaryV2(
                    category=cat.category,
                    total_debit=cat.total_debit,
                    debit_count=cat.debit_count,
                    total_credit=cat.total_credit,
                    credit_count=cat.credit_count,
                    net_amount=-cat.total_debit + cat.total_credit,  # Negative for spending
                    percentage=round((cat.total_debit / total_spending * 100), 1) if total_spending > 0 else 0
                ))
            
            # Income categories (categories with credits)
            if cat.total_credit > 0:
                income_categories.append(CategorySummaryV2(
                    category=cat.category,
                    total_debit=cat.total_debit,
                    debit_count=cat.debit_count,
                    total_credit=cat.total_credit,
                    credit_count=cat.credit_count,
                    net_amount=cat.total_credit - cat.total_debit,  # Positive for income
                    percentage=round((cat.total_credit / total_income * 100), 1) if total_income > 0 else 0
                ))
        
        # Sort by amount (descending)
        spending_categories.sort(key=lambda x: x.total_debit, reverse=True)
        income_categories.sort(key=lambda x: x.total_credit, reverse=True)
        
        return spending_categories, income_categories
    
    @staticmethod
    def transform_transactions(transactions: List[PortfolioCategorizedTransactionItem], page: int = 1, page_size: int = 50) -> tuple[List[TransactionV2], int]:
        """Transform transaction data with pagination"""
        total_count = len(transactions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_transactions = transactions[start_idx:end_idx]
        
        transformed = []
        for i, txn in enumerate(paginated_transactions):
            # Determine transaction type and amount
            if txn.debit_amount > 0:
                amount = -txn.debit_amount  # Negative for debits
                txn_type = TransactionType.DEBIT
            else:
                amount = txn.credit_amount  # Positive for credits
                txn_type = TransactionType.CREDIT
            
            transformed.append(TransactionV2(
                id=f"{txn.bank}_{txn.txn_date}_{i}_{uuid.uuid4().hex[:8]}",
                date=txn.txn_date,
                description=txn.description,
                amount=amount,
                category=txn.category,
                bank=txn.bank,
                balance=txn.balance_amount,
                transaction_type=txn_type,
                source_file=txn.source_file
            ))
        
        return transformed, total_count
    
    @staticmethod
    def transform_upi_analysis(upi_categories: List[PortfolioUpiAnalysisItem]) -> List[UPICategoryV2]:
        """Transform UPI analysis data"""
        total_upi_debit = sum(cat.total_debit for cat in upi_categories)
        total_upi_credit = sum(cat.total_credit for cat in upi_categories)
        
        transformed = []
        for cat in upi_categories:
            # Calculate percentage based on debit amount (spending focus)
            percentage = round((cat.total_debit / total_upi_debit * 100), 1) if total_upi_debit > 0 else 0
            
            transformed.append(UPICategoryV2(
                category=cat.category,
                total_debit=cat.total_debit,
                debit_count=cat.debit_count,
                total_credit=cat.total_credit,
                credit_count=cat.credit_count,
                net_amount=cat.total_credit - cat.total_debit,
                percentage=percentage
            ))
        
        # Sort by debit amount (descending)
        transformed.sort(key=lambda x: x.total_debit, reverse=True)
        
        return transformed
    
    @staticmethod
    def create_dashboard_response(
        overall_summary: PortfolioOverallSummaryData,
        categories: List[PortfolioCategorySummaryItem],
        transactions: List[PortfolioCategorizedTransactionItem]
    ) -> DashboardResponse:
        """Create dashboard response with all required data"""
        
        # Transform overall summary
        summary = APIv2Transformer.transform_overall_summary(overall_summary)
        
        # Transform categories
        spending_cats, income_cats = APIv2Transformer.transform_category_summary(categories)
        
        # Get top categories (limit to 5)
        top_spending = spending_cats[:5]
        top_income = income_cats[:5]
        
        # Get recent transactions (limit to 5)
        recent_txns, _ = APIv2Transformer.transform_transactions(transactions[-5:])
        
        return DashboardResponse(
            overall_summary=summary,
            top_spending_categories=top_spending,
            top_income_categories=top_income,
            recent_transactions=recent_txns
        )
    
    @staticmethod
    def create_categories_response(categories: List[PortfolioCategorySummaryItem]) -> CategoriesResponse:
        """Create categories response"""
        spending_cats, income_cats = APIv2Transformer.transform_category_summary(categories)
        
        total_spending = sum(cat.total_debit for cat in spending_cats)
        total_income = sum(cat.total_credit for cat in income_cats)
        
        return CategoriesResponse(
            spending_categories=spending_cats,
            income_categories=income_cats,
            total_spending=total_spending,
            total_income=total_income
        )
    
    @staticmethod
    def create_transactions_response(
        transactions: List[PortfolioCategorizedTransactionItem],
        overall_summary: PortfolioOverallSummaryData,
        page: int = 1,
        page_size: int = 50
    ) -> TransactionsResponse:
        """Create transactions response with pagination"""
        transformed_txns, total_count = APIv2Transformer.transform_transactions(transactions, page, page_size)
        total_pages = (total_count + page_size - 1) // page_size
        
        summary = APIv2Transformer.transform_overall_summary(overall_summary)
        
        return TransactionsResponse(
            transactions=transformed_txns,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary
        )
    
    @staticmethod
    def create_upi_response(upi_categories: List[PortfolioUpiAnalysisItem]) -> UPIAnalysisResponse:
        """Create UPI analysis response"""
        transformed_upi = APIv2Transformer.transform_upi_analysis(upi_categories)
        
        total_debit = sum(cat.total_debit for cat in transformed_upi)
        total_credit = sum(cat.total_credit for cat in transformed_upi)
        total_transactions = sum(cat.debit_count + cat.credit_count for cat in transformed_upi)
        
        return UPIAnalysisResponse(
            upi_categories=transformed_upi,
            total_upi_debit=total_debit,
            total_upi_credit=total_credit,
            total_upi_transactions=total_transactions,
            net_upi_amount=total_credit - total_debit
        )
