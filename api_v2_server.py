"""
FinanceAnalyzer Backend API v2 Server
FastAPI server providing REST APIs for Mint-like frontend
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import sys
import os
from pathlib import Path
import tempfile
import uuid
from typing import Optional, Dict, Any, List

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.finance_analyzer import FinanceAnalyzer
from src.data_transformer import DataTransformer
from src.api_v2_models import *
from src.api_v2_transformers import APIv2Transformer
from src.excel_models import PortfolioAnalysisData, PortfolioOverallSummaryData, PortfolioCategorySummaryItem, PortfolioUpiAnalysisItem, PortfolioUpiSummary, PortfolioCategorizedTransactionItem
import json
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="FinanceAnalyzer API v2",
    version="2.0.0",
    description="REST API for Mint-like personal finance frontend"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for analysis results
analysis_storage: Dict[str, PortfolioAnalysisData] = {}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def transform_analyzer_to_portfolio_data(analyzer) -> PortfolioAnalysisData:
    """Transform FinanceAnalyzer data to PortfolioAnalysisData format"""
    from datetime import datetime
    
    # Get the data from analyzer
    overall = analyzer.overall_summary
    category_df = analyzer.category_summary
    transactions_df = analyzer.categorized_df
    
    # Transform overall summary
    overall_summary = PortfolioOverallSummaryData(
        total_earned=float(overall.get('Total Credits', 0)),
        total_spent=float(overall.get('Total Spends (Debits)', 0)),
        net_portfolio_change=float(overall.get('Net Change', 0)),
        total_transactions=int(overall.get('Total Transactions', 0)),
        external_transactions=int(overall.get('Total Transactions', 0)),  # Simplified
        self_transfer_transactions=0,  # Default
        external_outflows=int(overall.get('Total Transactions', 0)),  # Simplified
        external_inflows=float(overall.get('Total Credits', 0)),
        net_portfolio_change_transactions=float(overall.get('Net Change', 0)),
        self_transfers_ignored=0,  # Default
        data_range_start="2024-01-01",  # Default - should be extracted from data
        data_range_end="2024-12-31",   # Default - should be extracted from data
        report_generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Transform category summary
    category_summary = []
    if category_df is not None:
        for _, row in category_df.iterrows():
            category_summary.append(PortfolioCategorySummaryItem(
                category=str(row.get('Category', '')),
                total_debit=float(row.get('Total Debit', 0)),
                debit_count=int(row.get('Debit Count', 0)),
                total_credit=float(row.get('Total Credit', 0)),
                credit_count=int(row.get('Credit Count', 0)),
                net_amount=float(row.get('Total Credit', 0)) - float(row.get('Total Debit', 0))
            ))
    
    # Transform transactions
    categorized_transactions = []
    if transactions_df is not None:
        for _, row in transactions_df.iterrows():
            categorized_transactions.append(PortfolioCategorizedTransactionItem(
                txn_date=str(row.get('Date', '')),
                value_date=str(row.get('Date', '')),
                cheque_no=str(row.get('Reference', '')),
                description=str(row.get('Description', '')),
                debit_amount=float(row.get('Debit', 0)),
                credit_amount=float(row.get('Credit', 0)),
                balance_amount=float(row.get('Balance', 0)),
                category=str(row.get('Category', '')),
                source_file=str(row.get('Source_File', '')),
                bank=str(row.get('Bank', '')),
                reference=str(row.get('Reference', '')),
                year=int(row.get('Year', 2024)),
                broad_category=str(row.get('Category', ''))
            ))
    
    # Create empty UPI data for now
    upi_summary = []
    upi_analysis = []
    
    return PortfolioAnalysisData(
        overall_summary=overall_summary,
        categorized_transactions=categorized_transactions,
        category_summary=category_summary,
        upi_summary=upi_summary,
        upi_analysis=upi_analysis
    )

def get_analysis_data(analysis_id: str) -> PortfolioAnalysisData:
    """Get analysis data by ID or raise 404"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return analysis_storage[analysis_id]

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "FinanceAnalyzer API v2 is running", "version": "2.0.0"}

# ============================================================================
# FILE UPLOAD & ANALYSIS
# ============================================================================

@app.post("/api/v2/analyze", tags=["Analysis"])
async def analyze_files(
    files: List[UploadFile] = File(...),
    from_date: Optional[str] = Query(None, description="Start date filter (MM-YYYY)"),
    to_date: Optional[str] = Query(None, description="End date filter (MM-YYYY)"),
    portfolio_mode: bool = Query(False, description="Enable portfolio analysis mode")
):
    """
    Upload and analyze bank statement files
    Returns analysis_id for subsequent API calls
    """
    try:
        analysis_id = str(uuid.uuid4())
        temp_files = []
        file_names = []
        
        # Save uploaded files temporarily
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            temp_files.append(temp_file.name)
            file_names.append(file.filename)
        
        # Process all files
        if len(temp_files) == 1:
            # Single file analysis
            analyzer = FinanceAnalyzer(temp_files[0])
            analyzer.load_data()
            analyzer.process_transactions()
            analyzer.generate_summaries()
            
            # Apply date filters if provided
            if from_date or to_date:
                analyzer.analyze_with_date_filter(from_date, to_date)
            
            # Transform to structured data
            analysis_data = transform_analyzer_to_portfolio_data(analyzer)
        else:
            # Multi-file analysis - use portfolio analysis v2 method
            from src.portfolio_analyzer import process_portfolio_files_v2
            try:
                result = process_portfolio_files_v2(temp_files)
                if result and len(result) == 2:
                    output_file, portfolio_data = result
                    
                    # Create analyzer for compatibility
                    analyzer = FinanceAnalyzer(temp_files[0])
                    analyzer.load_data()
                    analyzer.process_transactions()
                    
                    # Use portfolio_data directly as analysis_data
                    analysis_data = portfolio_data
                else:
                    raise Exception("Portfolio processing failed")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")
        
        # Store analysis results
        analysis_storage[analysis_id] = analysis_data
        
        # Cleanup temp files
        for temp_file in temp_files:
            os.unlink(temp_file)
        
        return {
            "analysis_id": analysis_id,
            "files_processed": len(files),
            "file_names": file_names,
            "status": "completed"
        }
        
    except Exception as e:
        # Cleanup temp files on error
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/api/v2/dashboard/{analysis_id}", response_model=DashboardResponse, tags=["Dashboard"])
async def get_dashboard(analysis_id: str):
    """Get dashboard data including summary, top categories, and recent transactions"""
    analysis_data = get_analysis_data(analysis_id)
    
    return APIv2Transformer.create_dashboard_response(
        overall_summary=analysis_data.overall_summary,
        categories=analysis_data.category_summary,
        transactions=analysis_data.categorized_transactions
    )

# ============================================================================
# CATEGORIES ENDPOINTS
# ============================================================================

@app.get("/api/v2/categories/{analysis_id}", response_model=CategoriesResponse, tags=["Categories"])
async def get_categories(analysis_id: str):
    """Get all categories data for spending and income analysis"""
    analysis_data = get_analysis_data(analysis_id)
    
    return APIv2Transformer.create_categories_response(analysis_data.category_summary)

# ============================================================================
# TRANSACTIONS ENDPOINTS
# ============================================================================

@app.get("/api/v2/transactions/{analysis_id}", response_model=TransactionsResponse, tags=["Transactions"])
async def get_transactions(
    analysis_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    search: Optional[str] = Query(None, description="Search in description")
):
    """Get paginated transactions with optional filtering"""
    analysis_data = get_analysis_data(analysis_id)
    
    # Apply filters
    transactions = analysis_data.categorized_transactions
    
    if category:
        transactions = [t for t in transactions if t.category.lower() == category.lower()]
    
    if transaction_type:
        if transaction_type == TransactionType.DEBIT:
            transactions = [t for t in transactions if t.debit_amount > 0]
        else:
            transactions = [t for t in transactions if t.credit_amount > 0]
    
    if search:
        search_lower = search.lower()
        transactions = [t for t in transactions if search_lower in t.description.lower()]
    
    return APIv2Transformer.create_transactions_response(
        transactions=transactions,
        overall_summary=analysis_data.overall_summary,
        page=page,
        page_size=page_size
    )

# ============================================================================
# UPI ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/api/v2/upi-analysis/{analysis_id}", response_model=UPIAnalysisResponse, tags=["UPI Analysis"])
async def get_upi_analysis(analysis_id: str):
    """Get UPI transaction analysis"""
    analysis_data = get_analysis_data(analysis_id)
    
    return APIv2Transformer.create_upi_response(analysis_data.upi_analysis)

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/v2/analysis/{analysis_id}/info", tags=["Utility"])
async def get_analysis_info(analysis_id: str):
    """Get basic information about an analysis"""
    analysis_data = get_analysis_data(analysis_id)
    
    return {
        "analysis_id": analysis_id,
        "total_transactions": len(analysis_data.categorized_transactions),
        "total_categories": len(analysis_data.category_summary),
        "date_range": {
            "start": analysis_data.overall_summary.data_range_start,
            "end": analysis_data.overall_summary.data_range_end
        },
        "last_updated": analysis_data.overall_summary.last_updated
    }

@app.get("/api/v2/analysis", tags=["Utility"])
async def list_analyses():
    """List all available analyses"""
    return {
        "analyses": [
            {
                "analysis_id": aid,
                "total_transactions": len(data.categorized_transactions),
                "date_range": {
                    "start": data.overall_summary.data_range_start,
                    "end": data.overall_summary.data_range_end
                }
            }
            for aid, data in analysis_storage.items()
        ]
    }

# ============================================================================
# NEW ENDPOINTS FOR MISSING UI SECTIONS
# ============================================================================

@app.get("/api/v2/accounts/{analysis_id}", response_model=AccountBalancesResponse, tags=["Accounts"])
async def get_account_balances(analysis_id: str):
    """Get account balances with calculated values"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get analysis data
    analysis_data = analysis_storage[analysis_id]
    net_change = analysis_data.overall_summary.net_portfolio_change
    
    # Bank account = max(net_change, 0) - never negative
    bank_balance = max(net_change, 0.0)
    
    # Default account structure with calculated bank balance
    accounts = [
        AccountBalance(account_type="checking", balance=bank_balance, account_name="Bank Account"),
        AccountBalance(account_type="savings", balance=0.0, account_name="Savings Account"),
        AccountBalance(account_type="credit_cards", balance=0.0, account_name="Credit Cards"),
        AccountBalance(account_type="investments", balance=0.0, account_name="Investments"),
        AccountBalance(account_type="loans", balance=0.0, account_name="Loans")
    ]
    
    return AccountBalancesResponse(
        accounts=accounts,
        total_balance=bank_balance
    )

@app.get("/api/v2/monthly-trend/{analysis_id}", response_model=MonthlyTrendResponse, tags=["Trends"])
async def get_monthly_trend(analysis_id: str):
    """Get monthly trend data parsed from actual transactions"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get analysis data
    analysis_data = analysis_storage[analysis_id]
    transactions = analysis_data.categorized_transactions
    
    # Parse monthly data from transactions
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    monthly_totals = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    
    for txn in transactions:
        try:
            # Parse transaction date (format: "2023-04-01" or "2023-04-01 00:00:00")
            date_str = txn.txn_date.split()[0]  # Get date part only
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date_obj.strftime("%Y-%m")  # "2024-08", "2024-07", etc.
            
            # Add to monthly totals
            if txn.credit_amount > 0:
                monthly_totals[month_key]["income"] += txn.credit_amount
            if txn.debit_amount > 0:
                monthly_totals[month_key]["expenses"] += txn.debit_amount
                
        except (ValueError, AttributeError) as e:
            # Skip invalid dates
            continue
    
    # Generate last 6 months from current date (Aug 2024 -> Feb 2024)
    current_date = datetime.now()
    last_6_months = []
    
    for i in range(6):
        month_date = current_date - timedelta(days=30 * i)  # Approximate month back
        month_date = month_date.replace(day=1)  # First day of month
        month_key = month_date.strftime("%Y-%m")
        month_name = month_date.strftime("%b")  # "Aug", "Jul", etc.
        
        last_6_months.append({
            "key": month_key,
            "name": month_name
        })
    
    # Reverse to get chronological order (Feb -> Aug)
    last_6_months.reverse()
    
    # Build response with actual data or 0 if no data
    monthly_data = []
    for month_info in last_6_months:
        month_key = month_info["key"]
        month_name = month_info["name"]
        
        income = monthly_totals.get(month_key, {}).get("income", 0.0)
        expenses = monthly_totals.get(month_key, {}).get("expenses", 0.0)
        savings = income - expenses
        
        monthly_data.append(MonthlyTrendItem(
            month=month_name,
            income=income,
            expenses=expenses,
            savings=savings
        ))
    
    return MonthlyTrendResponse(
        monthly_data=monthly_data,
        period_months=6
    )

@app.get("/api/v2/budget-progress/{analysis_id}", response_model=BudgetProgressResponse, tags=["Budget"])
async def get_budget_progress(analysis_id: str):
    """Get budget progress with default values"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Default budget categories with 100/100 values as requested
    categories = ["Food & Dining", "Transportation", "Shopping", "Entertainment", "Healthcare"]
    budget_items = [
        BudgetProgressItem(category=category, spent=100.0, budget=100.0, percentage=100.0)
        for category in categories
    ]
    
    return BudgetProgressResponse(
        budget_items=budget_items,
        total_budget=500.0,
        total_spent=500.0
    )

@app.get("/api/v2/upcoming-bills/{analysis_id}", response_model=UpcomingBillsResponse, tags=["Bills"])
async def get_upcoming_bills(analysis_id: str):
    """Get upcoming bills with default values"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Default bills with 0 amounts as requested
    bills = [
        UpcomingBill(name="Home Loan EMI", amount=0.0, due_date="2024-01-25", status="pending"),
        UpcomingBill(name="Credit Card Bill", amount=0.0, due_date="2024-01-28", status="pending"),
        UpcomingBill(name="Internet Bill", amount=0.0, due_date="2024-01-30", status="pending"),
        UpcomingBill(name="Mobile Bill", amount=0.0, due_date="2024-02-02", status="upcoming")
    ]
    
    return UpcomingBillsResponse(
        bills=bills,
        total_amount=0.0
    )

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponseV2(
            error=exc.detail,
            code=f"HTTP_{exc.status_code}",
            details={"path": str(request.url)}
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponseV2(
            error="Internal server error",
            code="INTERNAL_ERROR",
            details={"message": str(exc)}
        ).dict()
    )

# ============================================================================
# EMAIL TRANSACTION ENDPOINTS
# ============================================================================

@app.post("/api/v2/email/sync", tags=["Email Transactions"])
async def sync_email_transactions():
    """Sync transactions from email sources (Gmail)"""
    try:
        from email_transaction_service import EmailTransactionService
        
        service = EmailTransactionService()
        
        # Fetch email transactions
        email_transactions = service.fetch_email_transactions()
        
        # Convert to standard format
        standard_transactions = service.convert_to_standard_format(email_transactions)
        
        # Generate summary
        summary = service.get_email_transaction_summary(standard_transactions)
        
        return {
            "status": "success",
            "message": f"Synced {len(standard_transactions)} email transactions",
            "summary": summary,
            "transactions": standard_transactions[:10]  # Return first 10 for preview
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sync failed: {str(e)}")

@app.get("/api/v2/email/status", tags=["Email Transactions"])
async def get_email_sync_status():
    """Get email integration status"""
    try:
        from credentials.enhanced_gmail_reader import GmailTransactionReader
        import os
        
        reader = GmailTransactionReader()
        
        # Check if credentials exist
        creds_exist = os.path.exists("/Users/jmysethi/Downloads/client_secret_885429144379-als8fusnv1vqdo3oosna9j3glp77ckm5.apps.googleusercontent.com.json")
        token_exist = os.path.exists("credentials/token.json")
        
        status = {
            "credentials_configured": creds_exist,
            "authenticated": token_exist,
            "supported_banks": ["HSBC"],
            "last_sync": None  # TODO: Add last sync timestamp
        }
        
        return status
        
    except Exception as e:
        return {
            "credentials_configured": False,
            "authenticated": False,
            "error": str(e)
        }

@app.post("/api/v2/email/authenticate", tags=["Email Transactions"])
async def authenticate_email():
    """Authenticate with Gmail API"""
    try:
        from credentials.enhanced_gmail_reader import GmailTransactionReader
        
        reader = GmailTransactionReader()
        reader.authenticate()
        
        return {
            "status": "success",
            "message": "Gmail authentication successful"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
