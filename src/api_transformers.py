"""
API Transformers for FinanceAnalyzer
Transform internal data structures to API contract formats
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from .api_models import *
from .finance_analyzer import FinanceAnalyzer

class APITransformer:
    """Transform internal data to API contract format"""
    
    @staticmethod
    def to_overall_summary_response(
        analysis_id: str, 
        analyzer: FinanceAnalyzer
    ) -> OverallSummaryResponse:
        """Transform analyzer data to overall summary response"""
        
        # Get overall summary
        overall_summary_data = analyzer.overall_summary or {}
        overall_summary = OverallSummary(
            **{
                "Total Spends (Debits)": overall_summary_data.get("Total Spends (Debits)", 0),
                "Total Credits": overall_summary_data.get("Total Credits", 0),
                "Net Change": overall_summary_data.get("Net Change", 0),
                "Total Transactions": overall_summary_data.get("Total Transactions", 0)
            }
        )
        
        # Transform categories
        top_spending_categories = []
        top_earning_categories = []
        
        if analyzer.category_summary is not None and not analyzer.category_summary.empty:
            df = analyzer.category_summary
            
            spending_list = []
            earning_list = []
            
            # Check if 'Category' is a column or index
            if 'Category' in df.columns:
                # Category is a column, iterate over rows
                for _, row in df.iterrows():
                    category = str(row['Category'])
                    debit_amount = float(row.get('Total Debit', 0))
                    credit_amount = float(row.get('Total Credit', 0))
                    debit_count = int(row.get('Debit Count', 0))
                    credit_count = int(row.get('Credit Count', 0))
                    
                    if debit_amount > 0:
                        spending_list.append({
                            'Category': category,
                            'Total Debit': debit_amount,
                            'Debit Count': debit_count
                        })
                    
                    if credit_amount > 0:
                        earning_list.append({
                            'Category': category,
                            'Total Credit': credit_amount,
                            'Credit Count': credit_count
                        })
            else:
                # Category is the index
                for category in df.index:
                    debit_amount = float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0
                    credit_amount = float(df.loc[category, 'Total Credit']) if 'Total Credit' in df.columns else 0.0
                    debit_count = int(df.loc[category, 'Debit Count']) if 'Debit Count' in df.columns else 0
                    credit_count = int(df.loc[category, 'Credit Count']) if 'Credit Count' in df.columns else 0
                    
                    if debit_amount > 0:
                        spending_list.append({
                            'Category': str(category),
                            'Total Debit': debit_amount,
                            'Debit Count': debit_count
                        })
                    
                    if credit_amount > 0:
                        earning_list.append({
                            'Category': str(category),
                            'Total Credit': credit_amount,
                            'Credit Count': credit_count
                        })
            
            # Sort and take top 5
            top_spending_categories = sorted(spending_list, key=lambda x: x['Total Debit'], reverse=True)[:5]
            top_earning_categories = sorted(earning_list, key=lambda x: x['Total Credit'], reverse=True)[:5]
        
        # Get date range
        date_range = DateRange(start_date=None, end_date=None)
        if analyzer.categorized_df is not None and not analyzer.categorized_df.empty:
            if 'Txn Date' in analyzer.categorized_df.columns:
                dates = pd.to_datetime(analyzer.categorized_df['Txn Date'], errors='coerce')
                if not dates.isna().all():
                    date_range = DateRange(
                        start_date=dates.min().strftime('%Y-%m-%d'),
                        end_date=dates.max().strftime('%Y-%m-%d')
                    )
        
        return OverallSummaryResponse(
            analysis_id=analysis_id,
            overall_summary=overall_summary,
            top_spending_categories=top_spending_categories,
            top_earning_categories=top_earning_categories,
            top_categories=top_spending_categories,  # For frontend compatibility
            date_range=date_range,
            filter_info=FilterInfo()
        )
    
    @staticmethod
    def to_category_summary_response(
        analysis_id: str, 
        category_data
    ) -> CategorySummaryResponse:
        """Transform category data to category summary response"""
        
        categories_list = []
        
        # Handle portfolio_data category_summary (list of PortfolioCategorySummaryItem)
        if isinstance(category_data, list):
            for item in category_data:
                categories_list.append(
                    CategorySummaryItem(
                        Category=item.category,
                        **{
                            "Total Debit": item.total_debit,
                            "Debit Count": item.debit_count,
                            "Total Credit": item.total_credit,
                            "Credit Count": item.credit_count,
                            "Net Amount": item.net_amount,
                            "Transaction Type": "Mixed" if item.total_debit > 0 and item.total_credit > 0 else ("Debit" if item.total_debit > 0 else "Credit")
                        }
                    )
                )
        
        # Handle analyzer category_summary (pandas DataFrame) - fallback
        # Handle analyzer category_summary (pandas DataFrame) - fallback
        elif hasattr(category_data, 'category_summary') and category_data.category_summary is not None and not category_data.category_summary.empty:
            df = category_data.category_summary
            
            # Check if 'Category' is a column or index
            if 'Category' in df.columns:
                # Category is a column, iterate over rows
                for _, row in df.iterrows():
                    category = str(row['Category'])
                    debit_amount = float(row.get('Total Debit', 0))
                    credit_amount = float(row.get('Total Credit', 0))
                    debit_count = int(row.get('Debit Count', 0))
                    credit_count = int(row.get('Credit Count', 0))
                    net_amount = credit_amount - debit_amount
                    
                    # Determine transaction type
                    transaction_type = APITransformer._classify_transaction_type(
                        category, debit_amount, credit_amount
                    )
                    
                    categories_list.append(CategorySummaryItem(
                        Category=category,
                        **{
                            "Total Debit": debit_amount,
                            "Debit Count": debit_count,
                            "Total Credit": credit_amount,
                            "Credit Count": credit_count,
                            "Net Amount": net_amount,
                            "Transaction Type": transaction_type
                        }
                    ))
            else:
                # Category is the index
                for category in df.index:
                    debit_amount = float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0
                    credit_amount = float(df.loc[category, 'Total Credit']) if 'Total Credit' in df.columns else 0.0
                    debit_count = int(df.loc[category, 'Debit Count']) if 'Debit Count' in df.columns else 0
                    credit_count = int(df.loc[category, 'Credit Count']) if 'Credit Count' in df.columns else 0
                    net_amount = credit_amount - debit_amount
                    
                    # Determine transaction type
                    transaction_type = APITransformer._classify_transaction_type(
                        str(category), debit_amount, credit_amount
                    )
                    
                    categories_list.append(CategorySummaryItem(
                        Category=str(category),
                        **{
                            "Total Debit": debit_amount,
                            "Debit Count": debit_count,
                            "Total Credit": credit_amount,
                            "Credit Count": credit_count,
                            "Net Amount": net_amount,
                            "Transaction Type": transaction_type
                        }
                    ))
        
        return CategorySummaryResponse(
            analysis_id=analysis_id,
            category_summary=CategorySummaryData(category_summary=categories_list)
        )
    
    @staticmethod
    def to_portfolio_response(
        analysis_id: str, 
        portfolio_summary: Dict[str, Any], 
        analyzer: FinanceAnalyzer
    ) -> PortfolioResponse:
        """Transform portfolio data to portfolio response"""
        
        # Get external flows breakdown
        external_inflows_breakdown = []
        external_outflows_breakdown = []
        
        # Use breakdown data from portfolio_summary if available
        if "external_inflows_breakdown" in portfolio_summary:
            external_inflows_breakdown = portfolio_summary["external_inflows_breakdown"]
        
        if "external_outflows_breakdown" in portfolio_summary:
            external_outflows_breakdown = portfolio_summary["external_outflows_breakdown"]
        
        # Fallback to analyzer data if no breakdown provided
        elif analyzer and hasattr(analyzer, 'category_summary') and analyzer.category_summary is not None:
            df = analyzer.category_summary
            
            total_inflows = portfolio_summary.get("external_inflows", 0)
            total_outflows = portfolio_summary.get("external_outflows", 0)
            
            inflow_categories = []
            outflow_categories = []
            
            for category in df.index:
                credit_amount = float(df.loc[category, 'Total Credit']) if 'Total Credit' in df.columns else 0.0
                debit_amount = float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0
                credit_count = int(df.loc[category, 'Credit Count']) if 'Credit Count' in df.columns else 0
                debit_count = int(df.loc[category, 'Debit Count']) if 'Debit Count' in df.columns else 0
                
                # Skip self-transfer categories
                if 'self' in str(category).lower() or 'transfer' in str(category).lower():
                    continue
                
                if credit_amount > 0:
                    inflow_categories.append(FlowBreakdownItem(
                        category=str(category),
                        amount=credit_amount,
                        count=credit_count,
                        percentage=round((credit_amount / total_inflows * 100), 1) if total_inflows > 0 else 0
                    ))
                
                if debit_amount > 0:
                    outflow_categories.append(FlowBreakdownItem(
                        category=str(category),
                        amount=debit_amount,
                        count=debit_count,
                        percentage=round((debit_amount / total_outflows * 100), 1) if total_outflows > 0 else 0
                    ))
            
            external_inflows_breakdown = sorted(inflow_categories, key=lambda x: x.amount, reverse=True)
            external_outflows_breakdown = sorted(outflow_categories, key=lambda x: x.amount, reverse=True)
        
        portfolio_insights = PortfolioInsights(
            summary=PortfolioSummary(
                total_transactions=portfolio_summary.get("total_transactions", 0),
                external_transactions=portfolio_summary.get("external_transactions", 0),
                self_transfers_ignored=portfolio_summary.get("self_transfers_ignored", 
                                                           portfolio_summary.get("self_transfer_transactions", 0)),
                external_inflows=portfolio_summary.get("external_inflows", 0),
                external_outflows=portfolio_summary.get("external_outflows", 0),
                net_portfolio_change=portfolio_summary.get("net_portfolio_change", 
                                                         portfolio_summary.get("net_external_change", 0))
            ),
            external_inflows_breakdown=external_inflows_breakdown,
            external_outflows_breakdown=external_outflows_breakdown,
            note="Self-transfer transactions are completely ignored in portfolio analysis"
        )
        
        return PortfolioResponse(
            analysis_id=analysis_id,
            portfolio_insights=portfolio_insights
        )
    
    @staticmethod
    def to_upi_response(
        analysis_id: str, 
        upi_summary_data,
        upi_analysis_data
    ) -> UPIResponse:
        """Transform UPI data to UPI response with hierarchical structure"""
        
        # Create broad categories with expandable subcategories
        broad_categories = []
        
        if isinstance(upi_summary_data, list) and isinstance(upi_analysis_data, list):
            # Group subcategories by broad category
            subcategory_map = {}
            for item in upi_analysis_data:
                # Extract broad category from full category (UPI-BroadCategory-SubCategory)
                category_parts = item.category.split('-')
                if len(category_parts) >= 2:
                    broad_cat = category_parts[1]
                    if broad_cat not in subcategory_map:
                        subcategory_map[broad_cat] = []
                    
                    subcategory_map[broad_cat].append({
                        "category": item.category,
                        "total_debit": item.total_debit,
                        "total_credit": item.total_credit,
                        "net_amount": item.net_amount,
                        "transaction_count": item.debit_count + item.credit_count
                    })
            
            # Create broad categories with subcategories
            for summary_item in upi_summary_data:
                subcategories = subcategory_map.get(summary_item.category, [])
                
                broad_categories.append({
                    "broad_category": summary_item.category,
                    "total_amount": summary_item.total_amount,
                    "subcategories": subcategories,
                    "subcategory_count": len(subcategories)
                })
        
        # Calculate totals
        total_upi_amount = sum(cat["total_amount"] for cat in broad_categories)
        total_categories = len(broad_categories)
        total_subcategories = sum(cat["subcategory_count"] for cat in broad_categories)
        
        return UPIResponse(
            analysis_id=analysis_id,
            upi_analysis=UPIAnalysisData(
                summary=UPISummary(
                    total_upi_transactions=total_subcategories,
                    total_upi_debit=sum(sum(sub["total_debit"] for sub in cat["subcategories"]) for cat in broad_categories),
                    total_upi_credit=sum(sum(sub["total_credit"] for sub in cat["subcategories"]) for cat in broad_categories),
                    net_upi_amount=total_upi_amount
                ),
                upi_spending_categories=[],  # Can be populated later if needed
                upi_hierarchy={
                    cat["broad_category"]: UPIHierarchyItem(
                        total_debit=sum(sub["total_debit"] for sub in cat["subcategories"]),
                        total_credit=sum(sub["total_credit"] for sub in cat["subcategories"]),
                        net_amount=cat["total_amount"],
                        subcategories={
                            sub["category"]: UPISubcategory(
                                debit=sub["total_debit"],
                                credit=sub["total_credit"],
                                count=sub["transaction_count"]
                            ) for sub in cat["subcategories"]
                        }
                    ) for cat in broad_categories
                }
            )
        )
        
        df = analyzer.categorized_df
        upi_transactions = df[df['Category'].str.contains('UPI', na=False, case=False)]
        
        if upi_transactions.empty:
            return UPIResponse(
                analysis_id=analysis_id,
                upi_analysis=UPIAnalysisData(
                    summary=UPISummary(
                        total_upi_transactions=0,
                        total_upi_debit=0,
                        total_upi_credit=0,
                        net_upi_amount=0
                    ),
                    upi_spending_categories=[],
                    upi_hierarchy={}
                )
            )
        
        # Calculate UPI summary
        total_upi_debit = upi_transactions['Debit'].sum() if 'Debit' in upi_transactions.columns else 0
        total_upi_credit = upi_transactions['Credit'].sum() if 'Credit' in upi_transactions.columns else 0
        
        upi_summary = UPISummary(
            total_upi_transactions=len(upi_transactions),
            total_upi_debit=float(total_upi_debit),
            total_upi_credit=float(total_upi_credit),
            net_upi_amount=float(total_upi_credit - total_upi_debit)
        )
        
        # Get UPI categories and hierarchy
        upi_categories = []
        upi_hierarchy = {}
        
        if analyzer.category_summary is not None and not analyzer.category_summary.empty:
            df_summary = analyzer.category_summary
            
            for category in df_summary.index:
                if 'UPI' in str(category):
                    debit_amount = float(df_summary.loc[category, 'Total Debit']) if 'Total Debit' in df_summary.columns else 0.0
                    credit_amount = float(df_summary.loc[category, 'Total Credit']) if 'Total Credit' in df_summary.columns else 0.0
                    debit_count = int(df_summary.loc[category, 'Debit Count']) if 'Debit Count' in df_summary.columns else 0
                    credit_count = int(df_summary.loc[category, 'Credit Count']) if 'Credit Count' in df_summary.columns else 0
                    
                    upi_categories.append(UPICategoryItem(
                        category=str(category),
                        total_debit=debit_amount,
                        debit_count=debit_count,
                        total_credit=credit_amount,
                        credit_count=credit_count,
                        net_amount=credit_amount - debit_amount
                    ))
                    
                    # Build hierarchy
                    parts = str(category).split('-')
                    if len(parts) >= 3:  # UPI-MainCategory-SubCategory
                        main_cat = parts[1]
                        sub_cat = parts[2] if len(parts) > 2 else "Other"
                        
                        if main_cat not in upi_hierarchy:
                            upi_hierarchy[main_cat] = UPIHierarchyItem(
                                total_debit=0,
                                total_credit=0,
                                net_amount=0,
                                subcategories={}
                            )
                        
                        upi_hierarchy[main_cat].total_debit += debit_amount
                        upi_hierarchy[main_cat].total_credit += credit_amount
                        upi_hierarchy[main_cat].net_amount += (credit_amount - debit_amount)
                        
                        upi_hierarchy[main_cat].subcategories[sub_cat] = UPISubcategory(
                            debit=debit_amount,
                            credit=credit_amount,
                            count=debit_count + credit_count
                        )
        
        return UPIResponse(
            analysis_id=analysis_id,
            upi_analysis=UPIAnalysisData(
                summary=upi_summary,
                upi_spending_categories=upi_categories,
                upi_hierarchy=upi_hierarchy
            )
        )
    
    @staticmethod
    def to_transactions_response(
        analysis_id: str, 
        transaction_data
    ) -> TransactionsResponse:
        """Transform transaction data to transactions response"""
        
        transactions_list = []
        
        # Handle portfolio_data categorized_transactions (list of PortfolioCategorizedTransactionItem)
        if isinstance(transaction_data, list):
            # Take first 100 transactions
            limited_transactions = transaction_data[:100]
            
            for item in limited_transactions:
                transactions_list.append(Transaction(
                    Date=item.txn_date,
                    Description=item.description,
                    Amount=item.credit_amount - item.debit_amount,  # Net amount
                    Category=item.category,
                    Reference=item.reference,
                    Balance=item.balance_amount,
                    Debit=item.debit_amount,
                    Credit=item.credit_amount,
                    Transaction_Type="Mixed" if item.debit_amount > 0 and item.credit_amount > 0 else ("Debit" if item.debit_amount > 0 else "Credit"),
                    Source_File=item.source_file,
                    Bank=item.bank,
                    Year=item.year,
                    Broad_Category=item.broad_category
                ))
            
            return TransactionsResponse(
                analysis_id=analysis_id,
                transactions=transactions_list,
                total_shown=len(transactions_list),
                total_available=len(transaction_data),
                summary=TransactionSummary(
                    total_debits_shown=sum(t.Debit for t in transactions_list),
                    total_credits_shown=sum(t.Credit for t in transactions_list),
                    net_amount_shown=sum(t.Amount for t in transactions_list)
                ),
                note=f"Showing first {len(transactions_list)} of {len(transaction_data)} transactions"
            )
        
        # Handle analyzer categorized_df (pandas DataFrame) - fallback
        elif hasattr(transaction_data, 'categorized_df') and transaction_data.categorized_df is not None:
            df = transaction_data.categorized_df
            
            if df.empty:
                return TransactionsResponse(
                    analysis_id=analysis_id,
                    transactions=[],
                    total_shown=0,
                    total_available=0
                )
            
            # Take first 100 transactions
            limited_df = df.head(100)
            
            for _, row in limited_df.iterrows():
                debit_amount = float(row.get('Debit', 0) or 0)
                credit_amount = float(row.get('Credit', 0) or 0)
                
                transactions_list.append(Transaction(
                    Date=str(row.get('Txn Date', '')),
                    Description=str(row.get('Description', '')),
                    Amount=credit_amount - debit_amount,
                    Category=str(row.get('Category', '')),
                    Reference=str(row.get('Reference', '')),
                    Balance=float(row.get('Balance', 0) or 0),
                    Debit=debit_amount,
                    Credit=credit_amount,
                    Transaction_Type="Mixed" if debit_amount > 0 and credit_amount > 0 else ("Debit" if debit_amount > 0 else "Credit"),
                    Source_File=str(row.get('Source_File', '')),
                    Bank=str(row.get('Bank', '')),
                    Year=int(row.get('Year', 0) or 0),
                    Broad_Category=str(row.get('Broad_Category', '')) if row.get('Broad_Category') else None
                ))
            
            return TransactionsResponse(
                analysis_id=analysis_id,
                transactions=transactions_list,
                total_shown=len(transactions_list),
                total_available=len(df),
                summary=TransactionSummary(
                    total_debits_shown=sum(t.Debit for t in transactions_list),
                    total_credits_shown=sum(t.Credit for t in transactions_list),
                    net_amount_shown=sum(t.Amount for t in transactions_list)
                ),
                note=f"Showing first {len(transactions_list)} of {len(df)} transactions"
            )
        
        # No valid data
        else:
            return TransactionsResponse(
                analysis_id=analysis_id,
                transactions=[],
                total_shown=0,
                total_available=0,
                summary=TransactionSummary(
                    total_debits_shown=0,
                    total_credits_shown=0,
                    net_amount_shown=0
                ),
                note="No transaction data available"
            )
            return TransactionsResponse(
                analysis_id=analysis_id,
                transactions=[],
                total_shown=0,
                summary=TransactionSummary(
                    total_debits_shown=0,
                    total_credits_shown=0,
                    net_amount_shown=0
                ),
                note="No transactions found"
            )
        
        # Get first 100 transactions
        transactions_subset = df.head(100)
        transactions_list = []
        
        for _, row in transactions_subset.iterrows():
            transactions_list.append(Transaction(
                Date=str(row.get('Txn Date', '')),
                Description=str(row.get('Description', '')),
                Amount=float(row.get('Amount', 0)),
                Category=str(row.get('Category', '')),
                Reference=str(row.get('Reference', '')),
                Balance=float(row.get('Balance', 0)),
                Debit=float(row.get('Debit', 0)),
                Credit=float(row.get('Credit', 0)),
                Transaction_Type="Credit" if row.get('Credit', 0) > 0 else "Debit",
                Source_File=str(row.get('Source_File', '')),
                Bank=str(row.get('Bank', '')),
                Year=int(row.get('Year', 0)) if pd.notna(row.get('Year', 0)) else 0
            ))
        
        # Calculate summary
        total_debits_shown = transactions_subset['Debit'].sum() if 'Debit' in transactions_subset.columns else 0
        total_credits_shown = transactions_subset['Credit'].sum() if 'Credit' in transactions_subset.columns else 0
        
        return TransactionsResponse(
            analysis_id=analysis_id,
            transactions=transactions_list,
            total_shown=len(transactions_list),
            summary=TransactionSummary(
                total_debits_shown=float(total_debits_shown),
                total_credits_shown=float(total_credits_shown),
                net_amount_shown=float(total_credits_shown - total_debits_shown)
            ),
            note=f"Showing first {len(transactions_list)} transactions"
        )
    
    @staticmethod
    def _classify_transaction_type(category: str, debit_amount: float, credit_amount: float) -> str:
        """Classify transaction type based on category and amounts"""
        if debit_amount > 0 and credit_amount > 0:
            return "Mixed"
        elif credit_amount > 0:
            return "Income"
        elif 'transfer' in category.lower() or 'self' in category.lower():
            return "Transfer"
        elif 'atm' in category.lower() or 'cash' in category.lower():
            return "Cash Withdrawal"
        else:
            return "Expense"
