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
        
        # Initialize analyzer with first file
        analyzer = FinanceAnalyzer(temp_files[0])
        
        # Load and process data
        analyzer.load_data()
        analyzer.process_transactions()
        analyzer.generate_summaries()
        
        # Apply date filters if provided
        if from_date or to_date:
            # Use the analyze_with_date_filter method
            analyzer.analyze_with_date_filter(from_date, to_date)
        
        # Transform to structured data
        analysis_data = transform_analyzer_to_portfolio_data(analyzer)
        
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
            transactions = [t for t in transactions if t.debit > 0]
        else:
            transactions = [t for t in transactions if t.credit > 0]
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
