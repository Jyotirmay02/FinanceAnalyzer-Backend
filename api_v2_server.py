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
from src.database import init_db, get_db, DatabaseService, SessionLocal
from src.database.models import Transaction, Bank, Merchant, Category
import json
from datetime import datetime, timedelta

# Initialize database on startup
init_db()

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

@app.post("/api/v2/save/{analysis_id}", tags=["Analysis"])
async def save_analysis(analysis_id: str, db: SessionLocal = Depends(get_db)):
    """
    Save analyzed data from RAM to database with deduplication
    """
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    try:
        portfolio_data = analysis_storage[analysis_id]
        db_service = DatabaseService(db)
        
        # Extract transactions from categorized_transactions
        transactions = []
        for txn in portfolio_data.categorized_transactions:
            amount = txn.credit_amount if txn.credit_amount > 0 else -txn.debit_amount
            transactions.append({
                'date': txn.txn_date,
                'description': txn.description,
                'amount': amount,
                'category': txn.category,
                'bank': txn.bank,
                'type': 'credit' if amount > 0 else 'debit'
            })
        
        # Bulk add with deduplication
        result = db_service.bulk_add_transactions(transactions)
        
        # Clean up RAM after successful save
        del analysis_storage[analysis_id]
        
        return {
            "saved": result['saved'],
            "duplicates": result['duplicates'],
            "message": f"Saved {result['saved']} transactions, skipped {result['duplicates']} duplicates"
        }
    
    except Exception as e:
        import traceback
        error_detail = f"Save failed: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# ============================================================================
# NEW UPLOAD ENDPOINTS (Preview & Save Flow)
# ============================================================================

@app.post("/api/v2/upload/preview", tags=["Upload"])
async def upload_preview(files: List[UploadFile] = File(...)):
    """Upload files for preview (not saved to database yet)"""
    try:
        upload_id = str(uuid.uuid4())
        temp_files = []
        file_names = []
        
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            temp_files.append(temp_file.name)
            file_names.append(file.filename)
        
        from src.portfolio_analyzer import process_portfolio_files_v2
        result = process_portfolio_files_v2(temp_files)
        
        if not result or len(result) != 2:
            raise HTTPException(status_code=500, detail="Portfolio processing failed")
        
        output_file, portfolio_data = result
        
        db = SessionLocal()
        service = DatabaseService(db)
        temp_upload = service.create_temp_upload(
            upload_id=upload_id,
            filename=", ".join(file_names),
            data={"portfolio_data": portfolio_data.dict(), "file_names": file_names},
            hours=24
        )
        db.close()
        
        for temp_file in temp_files:
            os.unlink(temp_file)
        
        return {
            "upload_id": upload_id,
            "filename": ", ".join(file_names),
            "transaction_count": len(portfolio_data.categorized_transactions),
            "summary": {
                "total_spent": portfolio_data.overall_summary.total_spent,
                "total_earned": portfolio_data.overall_summary.total_earned,
                "net_change": portfolio_data.overall_summary.net_portfolio_change
            },
            "status": "preview"
        }
    except Exception as e:
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/upload/{upload_id}/save", tags=["Upload"])
async def save_upload(upload_id: str):
    """Save uploaded transactions to database"""
    db = SessionLocal()
    service = DatabaseService(db)
    
    temp_upload = service.get_temp_upload(upload_id)
    if not temp_upload:
        db.close()
        raise HTTPException(status_code=404, detail="Upload not found or expired")
    
    data = json.loads(temp_upload.data)
    portfolio_data = PortfolioAnalysisData(**data['portfolio_data'])
    
    transactions = []
    for txn in portfolio_data.categorized_transactions:
        try:
            txn_date = datetime.strptime(txn.txn_date, '%Y-%m-%d').date() if isinstance(txn.txn_date, str) else txn.txn_date
        except:
            continue
            
        transactions.append({
            'date': txn_date,
            'amount': abs(txn.debit_amount if txn.debit_amount > 0 else txn.credit_amount),
            'description': txn.description,
            'type': 'debit' if txn.debit_amount > 0 else 'credit',
            'bank': txn.bank or 'UNKNOWN',
            'category': txn.category or 'Uncategorized',
            'merchant': txn.description.split()[0] if txn.description else None,
            'balance': txn.balance_amount,
            'source_file': txn.source_file,
            'year': txn.year
        })
    
    result = service.bulk_add_transactions(transactions)
    service.delete_temp_upload(upload_id)
    db.close()
    
    return {
        "saved": result['saved'],
        "duplicates": result['duplicates'],
        "message": f"Saved {result['saved']} new, skipped {result['duplicates']} duplicates"
    }


@app.get("/api/v2/portfolio/summary", tags=["Portfolio"])
async def get_portfolio_summary():
    """Get summary of all saved transactions"""
    db = SessionLocal()
    service = DatabaseService(db)
    stats = service.get_summary_stats()
    categories = service.get_category_summary()
    db.close()
    
    return {"summary": stats, "categories": categories}

@app.get("/api/v2/portfolio/transactions", tags=["Portfolio"])
async def get_portfolio_transactions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get list of saved transactions"""
    db = SessionLocal()
    service = DatabaseService(db)
    transactions = service.get_transactions(limit=limit, offset=offset)
    
    # Get total count and stats
    stats = service.get_summary_stats()
    
    db.close()
    
    return {
        "transactions": transactions, 
        "count": len(transactions),
        "total_count": stats["total_transactions"],
        "total_spent": stats["total_spent"],
        "total_earned": stats["total_earned"],
        "debit_count": stats["debit_count"],
        "credit_count": stats["credit_count"]
    }

@app.post("/api/v2/portfolio/transactions", tags=["Portfolio"])
async def add_transaction(
    date: str,
    description: str,
    amount: float,
    type: str,
    category: str = "Uncategorized",
    bank: str = "Unknown"
):
    """Add a single transaction to database"""
    print(f"Adding transaction: date={date}, desc={description}, amount={amount}, type={type}")
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    result = service.add_transaction({
        'date': date,
        'description': description,
        'amount': amount,
        'category': category,
        'bank': bank,
        'type': type
    })
    
    db.close()
    
    if result:
        return {"success": True, "transaction_id": result.id}
    else:
        return {"success": False, "message": "Duplicate transaction"}

# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/api/v2/dashboard/{analysis_id}", response_model=DashboardResponse, tags=["Dashboard"])
async def get_dashboard(analysis_id: str):
    """Get dashboard data - supports both RAM and database"""
    
    if analysis_id == "database" or analysis_id not in analysis_storage:
        # Use database
        db = SessionLocal()
        service = DatabaseService(db)
        stats = service.get_summary_stats()
        categories = service.get_category_summary()
        recent = service.get_transactions(limit=10, offset=0)
        
        # Convert to expected format
        from src.excel_models import PortfolioCategorySummaryItem
        category_items = [
            PortfolioCategorySummaryItem(
                category=c['category'],
                total_debit=c['total'] if c['total'] < 0 else 0,
                debit_count=c['count'] if c['total'] < 0 else 0,
                total_credit=c['total'] if c['total'] > 0 else 0,
                credit_count=c['count'] if c['total'] > 0 else 0,
                net_amount=c['total'],
                transaction_count=c['count']
            )
            for c in categories
        ]
        
        from src.excel_models import PortfolioCategorizedTransactionItem
        transaction_items = []
        for t in recent:
            transaction_items.append(PortfolioCategorizedTransactionItem(
                txn_date=str(t.date),
                value_date='',
                cheque_no='',
                description=t.description or '',
                debit_amount=abs(t.amount) if t.type == 'debit' else 0,
                credit_amount=t.amount if t.type == 'credit' else 0,
                balance_amount=0,
                category=t.category.name if t.category else 'Uncategorized',
                source_file='',
                bank=t.bank.display_name if t.bank else 'Unknown',
                reference='',
                year=t.year or 0,
                broad_category=t.category.name if t.category else 'Uncategorized'
            ))
        
        db.close()
        
        from src.excel_models import PortfolioOverallSummaryData
        from datetime import datetime
        summary = PortfolioOverallSummaryData(
            total_earned=stats['total_earned'],
            total_spent=stats['total_spent'],
            net_portfolio_change=stats['net_change'],
            total_transactions=stats['total_transactions'],
            external_transactions=stats['total_transactions'],
            self_transfer_transactions=0,
            external_outflows=stats['debit_count'],
            external_inflows=stats['total_earned'],
            net_portfolio_change_transactions=stats['net_change'],
            self_transfers_ignored=0,
            data_range_start='',
            data_range_end='',
            last_updated='',
            report_generation_time=datetime.now().isoformat()
        )
        
        return APIv2Transformer.create_dashboard_response(
            overall_summary=summary,
            categories=category_items,
            transactions=transaction_items,
            calculate_summary_from_transactions=False
        )
    
    # Use RAM
    analysis_data = get_analysis_data(analysis_id)
    
    return APIv2Transformer.create_dashboard_response(
        overall_summary=analysis_data.overall_summary,
        categories=analysis_data.category_summary,
        transactions=analysis_data.categorized_transactions,
        calculate_summary_from_transactions=True
    )

# ============================================================================
# CATEGORIES ENDPOINTS
# ============================================================================

@app.get("/api/v2/categories/{analysis_id}", response_model=CategoriesResponse, tags=["Categories"])
async def get_categories(analysis_id: str):
    """Get all categories data - supports both RAM and database"""
    
    if analysis_id == "database" or analysis_id not in analysis_storage:
        # Use database
        db = SessionLocal()
        service = DatabaseService(db)
        categories = service.get_category_summary()
        db.close()
        
        from src.excel_models import PortfolioCategorySummaryItem
        category_items = [
            PortfolioCategorySummaryItem(
                category=c['category'],
                total_debit=abs(c['total']) if c['total'] < 0 else 0,
                debit_count=c['count'] if c['total'] < 0 else 0,
                total_credit=c['total'] if c['total'] > 0 else 0,
                credit_count=c['count'] if c['total'] > 0 else 0,
                net_amount=c['total'],
                transaction_count=c['count']
            )
            for c in categories
        ]
        
        return APIv2Transformer.create_categories_response(category_items)
    
    # Use RAM
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
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (debit/credit, case-insensitive)"),
    search: Optional[str] = Query(None, description="Search in description")
):
    """Get paginated transactions - supports both RAM and database"""
    
    # Check if using database mode
    if analysis_id == "database" or analysis_id not in analysis_storage:
        # Fetch from database
        db = SessionLocal()
        service = DatabaseService(db)
        
        # Normalize transaction_type to lowercase
        txn_type = transaction_type.lower() if transaction_type else None
        
        # Get full summary stats (not just from page)
        stats = service.get_summary_stats()
        
        # Get paginated transactions with filters
        db_transactions = service.get_transactions(
            txn_type=txn_type,
            search_term=search,
            limit=page_size, 
            offset=(page-1)*page_size
        )
        
        # Get filtered count for pagination
        total_count = service.get_filtered_count(
            txn_type=txn_type,
            search_term=search
        )
        
        # Convert to expected format BEFORE closing session
        from src.excel_models import PortfolioCategorizedTransactionItem
        transactions = []
        for t in db_transactions:
            transactions.append(PortfolioCategorizedTransactionItem(
                txn_date=str(t.date),
                value_date=str(t.value_date) if t.value_date else '',
                cheque_no=t.cheque_no or '',
                description=t.description or '',
                debit_amount=abs(t.amount) if t.type == 'debit' else 0,
                credit_amount=t.amount if t.type == 'credit' else 0,
                balance_amount=t.balance or 0,
                category=t.category.name if t.category else 'Uncategorized',
                source_file=t.source_file or '',
                bank=t.bank.display_name if t.bank else 'Unknown',
                reference=t.reference or '',
                year=t.year or 0,
                broad_category=t.category.name if t.category else 'Uncategorized'
            ))
        
        db.close()
        
        # Use actual summary from database
        from src.excel_models import PortfolioOverallSummaryData
        from datetime import datetime
        summary = PortfolioOverallSummaryData(
            total_earned=stats["total_earned"],
            total_spent=stats["total_spent"],
            net_portfolio_change=stats["net_change"],
            total_transactions=stats["total_transactions"],
            external_transactions=stats["total_transactions"],
            self_transfer_transactions=0,
            external_outflows=stats["debit_count"],
            external_inflows=stats["total_earned"],
            net_portfolio_change_transactions=stats["net_change"],
            self_transfers_ignored=0,
            data_range_start='',
            data_range_end='',
            last_updated='',
            report_generation_time=datetime.now().isoformat()
        )
        
        return APIv2Transformer.create_transactions_response(
            transactions=transactions,
            overall_summary=summary,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_earned=stats["total_earned"],
            total_spent=stats["total_spent"]
        )
    
    # Use RAM data
    analysis_data = analysis_storage[analysis_id]
    transactions = analysis_data.categorized_transactions
    
    if category:
        transactions = [t for t in transactions if t.category.lower() == category.lower()]
    
    if transaction_type:
        txn_type_lower = transaction_type.lower()
        if txn_type_lower == 'debit':
            transactions = [t for t in transactions if t.debit_amount > 0]
        elif txn_type_lower == 'credit':
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
    """Get monthly trend data parsed from actual transactions - supports both RAM and database"""
    
    # Get transactions from database or RAM
    if analysis_id == "database" or analysis_id not in analysis_storage:
        # Use database
        db = SessionLocal()
        service = DatabaseService(db)
        db_transactions = service.get_transactions(limit=10000, offset=0)
        
        # Convert to expected format
        from src.excel_models import PortfolioCategorizedTransactionItem
        transactions = []
        for t in db_transactions:
            transactions.append(PortfolioCategorizedTransactionItem(
                txn_date=str(t.date),
                value_date='',
                cheque_no='',
                description=t.description or '',
                debit_amount=abs(t.amount) if t.type == 'debit' else 0,
                credit_amount=t.amount if t.type == 'credit' else 0,
                balance_amount=0,
                category=t.category.name if t.category else 'Uncategorized',
                source_file='',
                bank=t.bank.display_name if t.bank else 'Unknown',
                reference='',
                year=t.year or 0,
                broad_category=t.category.name if t.category else 'Uncategorized'
            ))
        db.close()
    else:
        # Get analysis data from RAM
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
async def sync_email_transactions(days_back: int = 15):
    """Sync transactions from email sources (Gmail)
    
    Args:
        days_back: Number of days to look back (default: 15)
    """
    try:
        # Import your existing Gmail reader
        sys.path.append(str(Path(__file__).parent / "credentials"))
        from enhanced_gmail_reader import GmailTransactionReader
        
        # Get all configured email accounts from token files
        credentials_dir = Path(__file__).parent / "credentials"
        token_files = list(credentials_dir.glob("token_*.json"))
        email_accounts = [f.stem.replace("token_", "") for f in token_files]
        
        if not email_accounts:
            return {
                "status": "error",
                "message": "No email accounts configured",
                "summary": {"total_transactions": 0, "accounts_synced": 0, "banks_found": [], "errors": []}
            }
        
        all_transactions = {}
        errors = []
        
        for email in email_accounts:
            try:
                reader = GmailTransactionReader(email)
                reader.authenticate(email)
                
                # Use the correct method - get_all_bank_transactions
                bank_transactions = reader.get_all_bank_transactions(days_back=days_back)
                
                # Flatten transactions and add email source
                for bank, transactions in bank_transactions.items():
                    for transaction in transactions:
                        transaction['email_account'] = email
                        transaction['source'] = 'email_api'
                        transaction['bank'] = bank
                
                all_transactions[email] = bank_transactions
                
            except Exception as e:
                error_msg = f"Failed to sync {email}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
                continue
        
        # Flatten all transactions for summary
        flat_transactions = []
        banks_found = set()
        
        for email, bank_data in all_transactions.items():
            for bank, transactions in bank_data.items():
                flat_transactions.extend(transactions)
                if transactions:  # Only add bank if it has transactions
                    banks_found.add(bank)
        
        # Save to database
        db = SessionLocal()
        saved_count = 0
        duplicate_count = 0
        
        print(f"DEBUG: Attempting to save {len(flat_transactions)} transactions to database")
        
        try:
            for txn in flat_transactions:
                try:
                    print(f"DEBUG: Processing transaction: {txn.get('date')} - {txn.get('merchant')} - {txn.get('amount')}")
                    
                    # Get or create bank first
                    bank_name = txn.get('bank', 'Unknown')
                    bank = db.query(Bank).filter(Bank.code == bank_name).first()
                    if not bank:
                        bank = Bank(code=bank_name, display_name=bank_name, type='unknown')
                        db.add(bank)
                        db.flush()
                    
                    # Get or create merchant
                    merchant_name = txn.get('merchant', 'Unknown')
                    merchant = db.query(Merchant).filter(Merchant.name == merchant_name).first()
                    if not merchant:
                        merchant = Merchant(name=merchant_name)
                        db.add(merchant)
                        db.flush()
                    
                    # Parse date
                    date_str = txn.get('date')
                    if isinstance(date_str, str):
                        from datetime import datetime
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        date_obj = date_str
                    
                    # Check for duplicates with bank_id
                    existing = db.query(Transaction).filter(
                        Transaction.date == date_obj,
                        Transaction.amount == abs(float(txn.get('amount', 0))),
                        Transaction.description == merchant_name,
                        Transaction.bank_id == bank.id
                    ).first()
                    
                    if existing:
                        duplicate_count += 1
                        print(f"DEBUG: Duplicate found, skipping")
                        continue
                    
                    # Determine transaction type
                    txn_type = txn.get('transaction_type') or txn.get('type') or 'debit'
                    
                    # Create transaction
                    transaction = Transaction(
                        date=date_obj,
                        description=merchant_name,
                        amount=abs(float(txn.get('amount', 0))),
                        type=txn_type,
                        bank_id=bank.id,
                        merchant_id=merchant.id,
                        category_id=1  # Default category
                    )
                    db.add(transaction)
                    db.flush()  # Flush each transaction individually
                    saved_count += 1
                    
                except Exception as txn_error:
                    db.rollback()
                    if "UNIQUE constraint" in str(txn_error):
                        duplicate_count += 1
                        print(f"DEBUG: Duplicate constraint, skipping")
                    else:
                        print(f"DEBUG: Error saving transaction: {str(txn_error)}")
                    continue
            
            db.commit()
            print(f"DEBUG: Successfully saved {saved_count} transactions")
        except Exception as e:
            db.rollback()
            print(f"Database error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
        
        # Generate summary
        summary = {
            "total_transactions": len(flat_transactions),
            "saved_to_db": saved_count,
            "duplicates_skipped": duplicate_count,
            "accounts_synced": len(all_transactions),
            "banks_found": list(banks_found),
            "errors": errors,
            "date_range": {
                "from": f"{days_back} days ago",
                "to": "now"
            }
        }
        
        return {
            "status": "success" if flat_transactions else "partial",
            "message": f"Synced {len(flat_transactions)} email transactions from {len(all_transactions)}/{len(email_accounts)} accounts",
            "summary": summary,
            "transactions": flat_transactions[:20]  # Return first 20 for preview
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sync failed: {str(e)}")

@app.get("/api/v2/email/transactions", tags=["Email Transactions"])
async def get_email_transactions(
    email_account: Optional[str] = Query(None, description="Filter by email account"),
    bank: Optional[str] = Query(None, description="Filter by bank"),
    days: int = Query(30, description="Number of days to fetch")
):
    """Get email transactions with optional filters"""
    try:
        sys.path.append(str(Path(__file__).parent / "credentials"))
        from enhanced_gmail_reader import GmailTransactionReader
        
        email_accounts = ["jyotirmays123@gmail.com", "jotirmays123@gmail.com"]
        if email_account:
            email_accounts = [email_account]
        
        all_transactions = []
        
        for email in email_accounts:
            try:
                reader = GmailTransactionReader(email)
                reader.authenticate(email)
                
                # Get all bank transactions
                bank_transactions = reader.get_all_bank_transactions()
                
                # Flatten and filter
                for bank_name, transactions in bank_transactions.items():
                    # Filter by bank if specified
                    if bank and bank_name.upper() != bank.upper():
                        continue
                    
                    # Add metadata to each transaction
                    for transaction in transactions:
                        transaction['email_account'] = email
                        transaction['source'] = 'email_api'
                        transaction['bank'] = bank_name
                        all_transactions.append(transaction)
                
            except Exception as e:
                print(f"Failed to fetch from {email}: {str(e)}")
                continue
        
        return {
            "status": "success",
            "count": len(all_transactions),
            "transactions": all_transactions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch email transactions: {str(e)}")

@app.get("/api/v2/email/status", tags=["Email Transactions"])
async def get_email_sync_status():
    """Get email integration status"""
    try:
        sys.path.append(str(Path(__file__).parent / "credentials"))
        from enhanced_gmail_reader import GmailTransactionReader
        import os
        
        # Check credentials for each account
        email_accounts = ["jyotirmays123@gmail.com", "jotirmays123@gmail.com"]
        account_status = {}
        
        for email in email_accounts:
            token_file = f"credentials/token_{email}.pickle"
            account_status[email] = {
                "authenticated": os.path.exists(token_file),
                "token_file": token_file
            }
        
        creds_exist = os.path.exists("credentials/credentials.json")
        
        status = {
            "credentials_configured": creds_exist,
            "accounts": account_status,
            "supported_banks": ["HSBC", "ICICI", "IndusInd"],
            "total_accounts": len(email_accounts),
            "authenticated_accounts": sum(1 for acc in account_status.values() if acc["authenticated"])
        }
        
        return status
        
    except Exception as e:
        return {
            "credentials_configured": False,
            "accounts": {},
            "error": str(e)
        }

@app.post("/api/v2/email/add", tags=["Email Transactions"])
async def add_email_account(email: str = Query(..., description="Email address to add")):
    """Add new email account with OAuth authentication"""
    try:
        sys.path.append(str(Path(__file__).parent / "credentials"))
        from enhanced_gmail_reader import GmailTransactionReader
        
        # Validate email format
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid email address")
        
        # Check if token already exists
        token_file = Path(__file__).parent / "credentials" / f"token_{email}.json"
        if token_file.exists():
            return {
                "status": "error",
                "message": f"Email account {email} is already configured"
            }
        
        # Force new authentication by creating fresh reader instance
        reader = GmailTransactionReader(email)
        reader.creds = None  # Clear any cached credentials
        creds = reader.authenticate(email)
        
        if not creds or not creds.valid:
            raise HTTPException(status_code=500, detail="Authentication failed")
        
        return {
            "status": "success",
            "email": email,
            "message": f"Successfully added and authenticated {email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add email account: {str(e)}")

@app.delete("/api/v2/email/remove", tags=["Email Transactions"])
async def remove_email_account(email: str = Query(..., description="Email address to remove")):
    """Remove email account and delete token file"""
    try:
        token_file = Path(__file__).parent / "credentials" / f"token_{email}.json"
        
        if token_file.exists():
            token_file.unlink()
            return {
                "status": "success",
                "email": email,
                "message": f"Successfully removed {email}"
            }
        else:
            return {
                "status": "success",
                "email": email,
                "message": f"Token file not found for {email}"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove email account: {str(e)}")

@app.get("/api/v2/email/list", tags=["Email Transactions"])
async def list_email_accounts():
    """List all configured email accounts"""
    try:
        credentials_dir = Path(__file__).parent / "credentials"
        token_files = list(credentials_dir.glob("token_*.json"))
        
        emails = []
        for token_file in token_files:
            # Extract email from filename: token_email@domain.com.json
            email = token_file.stem.replace("token_", "")
            emails.append(email)
        
        return {
            "status": "success",
            "emails": sorted(emails),
            "count": len(emails)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list email accounts: {str(e)}")

@app.delete("/api/v2/data/clear", tags=["Data Management"])
async def clear_all_data():
    """Clear all data from database (for testing)"""
    try:
        db = SessionLocal()
        try:
            # Delete all transactions
            db.query(Transaction).delete()
            
            # Delete all categories except default
            db.query(Category).filter(Category.id > 1).delete()
            
            # Delete all banks except default
            db.query(Bank).filter(Bank.id > 1).delete()
            
            # Delete all merchants
            db.query(Merchant).delete()
            
            db.commit()
            
            return {
                "status": "success",
                "message": "All data cleared successfully"
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

@app.post("/api/v2/email/authenticate", tags=["Email Transactions"])
async def authenticate_email(email_account: Optional[str] = Query(None, description="Email account to authenticate")):
    """Authenticate with Gmail API for specific account"""
    try:
        sys.path.append(str(Path(__file__).parent / "credentials"))
        from enhanced_gmail_reader import GmailTransactionReader
        
        email_accounts = ["jyotirmays123@gmail.com", "jotirmays123@gmail.com"]
        if email_account:
            email_accounts = [email_account]
        
        results = {}
        
        for email in email_accounts:
            try:
                reader = GmailTransactionReader(email)
                creds = reader.authenticate(email)
                
                results[email] = {
                    "status": "success",
                    "authenticated": True,
                    "message": f"Successfully authenticated {email}"
                }
                
            except Exception as e:
                results[email] = {
                    "status": "error",
                    "authenticated": False,
                    "error": str(e)
                }
        
        return {
            "status": "completed",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
