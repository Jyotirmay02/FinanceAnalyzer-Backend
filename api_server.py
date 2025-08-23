"""
FinanceAnalyzer Backend API Server
FastAPI server providing REST APIs for financial analysis
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
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
from src.api_models import *
from src.api_transformers import APITransformer
from src.excel_models import PortfolioAnalysisData, PortfolioOverallSummaryData, PortfolioCategorySummaryItem, PortfolioUpiAnalysisItem, PortfolioUpiSummary, PortfolioCategorizedTransactionItem
import json
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="FinanceAnalyzer API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for analysis results
analysis_storage: Dict[str, Dict[str, Any]] = {}

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check"""
    return HealthResponse()

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_files(
    files: List[UploadFile] = File(...),
    from_date: Optional[str] = Form(None),
    to_date: Optional[str] = Form(None),
    portfolio_mode: Optional[str] = Form(None)
):
    """Upload and analyze financial files"""
    # Convert portfolio_mode string to boolean
    portfolio_mode_bool = portfolio_mode and portfolio_mode.lower() in ['true', '1', 'yes']
    
    # Validate file count
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed")
    
    # Save uploaded files temporarily
    temp_files = []
    file_names = []
    
    try:
        for file in files:
            file_names.append(file.filename)
            content = await file.read()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}")
            temp_file.write(content)
            temp_file.close()
            temp_files.append(temp_file.name)
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Perform analysis
        if portfolio_mode_bool:
            # Portfolio analysis using v2 method
            from src.portfolio_analyzer import process_portfolio_files_v2
            try:
                result = process_portfolio_files_v2(temp_files)
                if result and len(result) == 2:
                    output_file, portfolio_data = result
                    
                    # Create analyzer for compatibility
                    analyzer = FinanceAnalyzer(temp_files[0])
                    analyzer.load_data()
                    analyzer.process_transactions()
                    
                    analysis_storage[analysis_id] = {
                        "type": "portfolio",
                        "analyzer": analyzer,
                        "output_file": output_file,
                        "portfolio_data": portfolio_data,
                        "files": file_names
                    }
                else:
                    raise Exception("Portfolio processing failed")
            except Exception as e:
                import traceback
                raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")
        elif len(temp_files) == 1:
            # Single file analysis
            analyzer = FinanceAnalyzer(temp_files[0], from_date=from_date, to_date=to_date)
            analyzer.load_data()
            analyzer.process_transactions()
            analyzer.generate_summaries()
            output_file = analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "single",
                "analyzer": analyzer,
                "output_file": output_file,
                "files": file_names
            }
        else:
            # Multi-file analysis
            analyzers = []
            for temp_file in temp_files:
                analyzer = FinanceAnalyzer(temp_file, from_date=from_date, to_date=to_date)
                analyzer.load_data()
                analyzer.process_transactions()
                analyzers.append(analyzer)
            
            # Use first analyzer as primary
            primary_analyzer = analyzers[0]
            primary_analyzer.generate_summaries()
            output_file = primary_analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "multi",
                "analyzer": primary_analyzer,
                "analyzers": analyzers,
                "output_file": output_file,
                "files": file_names
            }
        
        return AnalyzeResponse(
            analysis_id=analysis_id,
            files_processed=len(files),
            file_names=file_names
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

@app.get("/api/summary/overall/{analysis_id}", response_model=OverallSummaryResponse)
async def get_overall_summary(analysis_id: str):
    """Get overall financial summary with top categories and date range"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        # Ensure overall summary is in correct format
        if analyzer.overall_summary is None or 'Total Spends (Debits)' not in analyzer.overall_summary:
            analyzer.overall_summary = DataTransformer.ensure_standard_format(analyzer)
        
        result = APITransformer.to_overall_summary_response(analysis_id, analyzer)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary/categories/{analysis_id}", response_model=CategorySummaryResponse)
async def get_category_summary(analysis_id: str):
    """Get detailed category-wise summary"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        portfolio_data = analysis_data["portfolio_data"]
        return APITransformer.to_category_summary_response(analysis_id, portfolio_data.category_summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/{analysis_id}", response_model=TransactionsResponse)
async def get_transactions(analysis_id: str):
    """Get transaction list (first 100 transactions)"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        if "portfolio_data" in analysis_data:
            portfolio_data = analysis_data["portfolio_data"]
            return APITransformer.to_transactions_response(analysis_id, portfolio_data.categorized_transactions)
        else:
            # Fallback to analyzer for old data
            analyzer = analysis_data["analyzer"]
            return APITransformer.to_transactions_response(analysis_id, analyzer)
        
    except Exception as e:
        return TransactionsResponse(
            analysis_id=analysis_id,
            transactions=[],
            total_shown=0,
            summary=TransactionSummary(
                total_debits_shown=0,
                total_credits_shown=0,
                net_amount_shown=0
            ),
            note=f"Error: {str(e)}"
        )

@app.get("/api/analysis/portfolio/{analysis_id}", response_model=PortfolioResponse)
async def get_portfolio_analysis(analysis_id: str):
    """Get portfolio-specific analysis with external flows breakdown"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        
        # Use stored portfolio_data if available
        if "portfolio_data" in analysis_data and analysis_data["portfolio_data"]:
            portfolio_data = analysis_data["portfolio_data"]
            analyzer = analysis_data["analyzer"]
            
            # Calculate external flows from category_summary excluding Self Transfer
            total_inflows = sum(item.total_credit for item in portfolio_data.category_summary if item.category != "Self Transfer")
            total_outflows = sum(item.total_debit for item in portfolio_data.category_summary if item.category != "Self Transfer")
            
            # Create breakdown arrays
            external_inflows_breakdown = []
            external_outflows_breakdown = []
            
            for item in portfolio_data.category_summary:
                if item.category == "Self Transfer":
                    continue
                    
                if item.total_credit > 0:
                    external_inflows_breakdown.append({
                        "category": item.category,
                        "amount": item.total_credit,
                        "count": item.credit_count,
                        "percentage": round((item.total_credit / total_inflows * 100), 1) if total_inflows > 0 else 0
                    })
                
                if item.total_debit > 0:
                    external_outflows_breakdown.append({
                        "category": item.category,
                        "amount": item.total_debit,
                        "count": item.debit_count,
                        "percentage": round((item.total_debit / total_outflows * 100), 1) if total_outflows > 0 else 0
                    })
            
            # Sort by amount descending
            external_inflows_breakdown.sort(key=lambda x: x["amount"], reverse=True)
            external_outflows_breakdown.sort(key=lambda x: x["amount"], reverse=True)
            
            # Get self transfer count
            self_transfer_item = next((item for item in portfolio_data.category_summary if item.category == "Self Transfer"), None)
            self_transfers_count = (self_transfer_item.debit_count + self_transfer_item.credit_count) if self_transfer_item else 0
            
            # Extract summary from portfolio_data for backward compatibility
            portfolio_summary = {
                'external_inflows': total_inflows,
                'external_outflows': total_outflows,
                'net_external_change': total_inflows - total_outflows,
                'total_transactions': portfolio_data.overall_summary.total_transactions,
                'external_transactions': portfolio_data.overall_summary.external_transactions,
                'self_transfers_ignored': self_transfers_count,
                'external_inflows_breakdown': external_inflows_breakdown,
                'external_outflows_breakdown': external_outflows_breakdown
            }
            
            return APITransformer.to_portfolio_response(analysis_id, portfolio_summary, analyzer)
        
        # Fallback for non-portfolio analysis
        analyzer = analysis_data["analyzer"]
        
        if not analyzer or not hasattr(analyzer, 'categorized_df') or analyzer.categorized_df is None:
            # Return empty portfolio response
            return PortfolioResponse(
                analysis_id=analysis_id,
                portfolio_insights=PortfolioInsights(
                    summary=PortfolioSummary(
                        total_transactions=0,
                        external_transactions=0,
                        self_transfers_ignored=0,
                        external_inflows=0,
                        external_outflows=0,
                        net_portfolio_change=0
                    ),
                    external_inflows_breakdown=[],
                    external_outflows_breakdown=[],
                    note="No portfolio data available"
                )
            )
        
        # Basic portfolio calculation for fallback
        df = analyzer.categorized_df
        self_transfers = df[df['Category'].str.contains('Self Transfer', na=False)]
        external_transactions = df[~df['Category'].str.contains('Self Transfer', na=False)]
        
        total_transactions = len(df)
        external_count = len(external_transactions)
        self_transfer_count = len(self_transfers)
        
        external_inflows = external_transactions['Credit'].sum() if 'Credit' in external_transactions.columns else 0
        external_outflows = external_transactions['Debit'].sum() if 'Debit' in external_transactions.columns else 0
        net_portfolio_change = external_inflows - external_outflows
        
        # Create basic portfolio summary for transformer
        basic_portfolio_summary = {
            "total_transactions": int(total_transactions),
            "external_transactions": int(external_count),
            "self_transfers_ignored": int(self_transfer_count),
            "external_inflows": float(external_inflows),
            "external_outflows": float(external_outflows),
            "net_portfolio_change": float(net_portfolio_change)
        }
        
        return APITransformer.to_portfolio_response(analysis_id, basic_portfolio_summary, analyzer)
        
    except Exception as e:
        # Return error response in correct format
        return PortfolioResponse(
            analysis_id=analysis_id,
            portfolio_insights=PortfolioInsights(
                summary=PortfolioSummary(
                    total_transactions=0,
                    external_transactions=0,
                    self_transfers_ignored=0,
                    external_inflows=0,
                    external_outflows=0,
                    net_portfolio_change=0
                ),
                external_inflows_breakdown=[],
                external_outflows_breakdown=[],
                note=f"Error: {str(e)}"
            )
        )

@app.get("/api/analysis/upi/{analysis_id}", response_model=UPIResponse)
async def get_upi_analysis(analysis_id: str):
    """Get UPI-specific analysis with hierarchy"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        if "portfolio_data" in analysis_data:
            portfolio_data = analysis_data["portfolio_data"]
            return APITransformer.to_upi_response(analysis_id, portfolio_data.upi_summary, portfolio_data.upi_analysis)
        else:
            # Fallback to analyzer for old data
            analyzer = analysis_data["analyzer"]
            return APITransformer.to_upi_response(analysis_id, [], [])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/{analysis_id}")
async def export_analysis(analysis_id: str, format: str = "excel"):
    """Export analysis results"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        
        if format.lower() == "csv":
            # Export as CSV
            analyzer = analysis_data["analyzer"]
            summary_df = pd.DataFrame([analyzer.overall_summary])
            
            csv_file = f"/tmp/analysis_{analysis_id}.csv"
            summary_df.to_csv(csv_file, index=False)
            
            return FileResponse(
                csv_file,
                media_type="text/csv",
                filename=f"financial_analysis_{analysis_id}.csv"
            )
        else:
            # Export as Excel (default)
            output_file = analysis_data.get("output_file")
            
            if output_file and os.path.exists(output_file):
                return FileResponse(
                    output_file,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename=f"financial_analysis_{analysis_id}.xlsx"
                )
            else:
                raise HTTPException(status_code=404, detail="Export file not found")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

def _create_portfolio_analysis_data(analyzer, portfolio_summary) -> PortfolioAnalysisData:
    """Create PortfolioAnalysisData from analyzer and portfolio summary"""
    
    # Create overall summary
    overall_summary = PortfolioOverallSummaryData(
        total_earned=float(portfolio_summary.get('external_inflows', 0)) if portfolio_summary else 0,
        total_spent=float(portfolio_summary.get('external_outflows', 0)) if portfolio_summary else 0,
        net_portfolio_change=float(portfolio_summary.get('net_portfolio_change', 0)) if portfolio_summary else 0,
        total_transactions=int(portfolio_summary.get('total_transactions', 0)) if portfolio_summary else 0,
        external_transactions=int(portfolio_summary.get('external_transactions', 0)) if portfolio_summary else 0,
        self_transfer_transactions=int(portfolio_summary.get('self_transfers_ignored', 0)) if portfolio_summary else 0,
        external_outflows=int(portfolio_summary.get('external_transactions', 0)) if portfolio_summary else 0,
        external_inflows=float(portfolio_summary.get('external_inflows', 0)) if portfolio_summary else 0,
        net_portfolio_change_transactions=float(portfolio_summary.get('net_portfolio_change', 0)) if portfolio_summary else 0,
        self_transfers_ignored=int(portfolio_summary.get('self_transfers_ignored', 0)) if portfolio_summary else 0,
        data_range_start=analyzer.from_date or "N/A",
        data_range_end=analyzer.to_date or "N/A",
        report_generation_time=datetime.now().isoformat()
    )
    
    # Create categorized transactions
    categorized_transactions = []
    if hasattr(analyzer, 'categorized_df') and analyzer.categorized_df is not None:
        for _, row in analyzer.categorized_df.iterrows():
            transaction = PortfolioCategorizedTransactionItem(
                txn_date=str(row.get('Txn Date', '')),
                value_date=str(row.get('Value Date', '')),
                cheque_no=str(row.get('Cheque No.', '')),
                description=str(row.get('Description', '')),
                debit_amount=float(row.get('Debit', 0) or 0),
                credit_amount=float(row.get('Credit', 0) or 0),
                balance_amount=float(row.get('Balance', 0) or 0),
                category=str(row.get('Category', '')),
                source_file=str(row.get('Source File', '')),
                bank=str(row.get('Bank', '')),
                reference=str(row.get('Reference', '')),
                year=int(row.get('Year', 0) or 0),
                broad_category=str(row.get('Broad Category', ''))
            )
            categorized_transactions.append(transaction)
    
    # Create category summary
    category_summary = []
    if hasattr(analyzer, 'category_summary') and analyzer.category_summary is not None:
        for category, row in analyzer.category_summary.iterrows():
            summary_item = PortfolioCategorySummaryItem(
                category=str(category),
                total_debit=float(row.get('Total Debit', 0) or 0),
                debit_count=int(row.get('Debit Count', 0) or 0),
                total_credit=float(row.get('Total Credit', 0) or 0),
                credit_count=int(row.get('Credit Count', 0) or 0),
                net_amount=float(row.get('Net Amount', 0) or 0)
            )
            category_summary.append(summary_item)
    
    # Create UPI summary and analysis (placeholder for now)
    upi_summary = []
    upi_analysis = []
    categorized_transactions = []
    
    return PortfolioAnalysisData(
        overall_summary=overall_summary,
        categorized_transactions=categorized_transactions,
        category_summary=category_summary,
        upi_summary=upi_summary,
        upi_analysis=upi_analysis
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
