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

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    return obj

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
            # Portfolio analysis
            from src.portfolio_analyzer import process_portfolio_files
            try:
                result = process_portfolio_files(temp_files)
                if isinstance(result, tuple) and len(result) == 2:
                    output_file, portfolio_summary = result
                else:
                    output_file = result if result else None
                    portfolio_summary = None
            except Exception as e:
                print(f"Portfolio processing error: {e}")
                output_file = None
                portfolio_summary = None
            
            # Create analyzer for compatibility
            analyzer = FinanceAnalyzer(temp_files[0])
            analyzer.load_data()
            analyzer.process_transactions()

            analysis_storage[analysis_id] = {
                "type": "portfolio",
                "analyzer": analyzer,
                "output_file": output_file,
                "portfolio_summary": portfolio_summary,
                "files": file_names
            }
        elif len(temp_files) == 1:
            # Single file analysis
            analyzer = FinanceAnalyzer(temp_files[0], from_date=from_date, to_date=to_date)
            analyzer.load_data()
            analyzer.process_transactions()
            analyzer.generate_summaries()
            analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "single",
                "analyzer": analyzer,
                "output_file": analyzer.output_file,
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
            primary_analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "multi",
                "analyzer": primary_analyzer,
                "analyzers": analyzers,
                "output_file": primary_analyzer.output_file,
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
        
        return APITransformer.to_overall_summary_response(analysis_id, analyzer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary/categories/{analysis_id}", response_model=CategorySummaryResponse)
async def get_category_summary(analysis_id: str):
    """Get detailed category-wise summary"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        return APITransformer.to_category_summary_response(analysis_id, analyzer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/portfolio/{analysis_id}", response_model=PortfolioResponse)
async def get_portfolio_analysis(analysis_id: str):
    """Get portfolio-specific analysis with external flows breakdown"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        
        # Use stored portfolio summary if available
        if "portfolio_summary" in analysis_data and analysis_data["portfolio_summary"]:
            portfolio_summary = analysis_data["portfolio_summary"]
            analyzer = analysis_data["analyzer"]
            
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
        analyzer = analysis_storage[analysis_id]["analyzer"]
        return APITransformer.to_upi_response(analysis_id, analyzer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/{analysis_id}", response_model=TransactionsResponse)
async def get_transactions(analysis_id: str):
    """Get transaction list (first 100 transactions)"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.post("/api/analyze")
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
            # Portfolio analysis
            from src.portfolio_analyzer import process_portfolio_files
            try:
                result = process_portfolio_files(temp_files)
                if isinstance(result, tuple) and len(result) == 2:
                    output_file, portfolio_summary = result
                else:
                    output_file = result if result else None
                    portfolio_summary = None
            except Exception as e:
                print(f"Portfolio processing error: {e}")
                output_file = None
                portfolio_summary = None
            
            # Create analyzer for compatibility
            analyzer = FinanceAnalyzer(temp_files[0])
            analyzer.load_data()
            analyzer.process_transactions()
            
            analysis_storage[analysis_id] = {
                "type": "portfolio",
                "analyzer": analyzer,
                "output_file": output_file,
                "portfolio_summary": portfolio_summary,
                "files": file_names
            }
        elif len(temp_files) == 1:
            # Single file analysis
            analyzer = FinanceAnalyzer(temp_files[0], from_date=from_date, to_date=to_date)
            analyzer.load_data()
            analyzer.process_transactions()
            analyzer.generate_summaries()
            analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "single",
                "analyzer": analyzer,
                "output_file": analyzer.output_file,
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
            primary_analyzer.export_results()
            
            analysis_storage[analysis_id] = {
                "type": "multi",
                "analyzer": primary_analyzer,
                "analyzers": analyzers,
                "output_file": primary_analyzer.output_file,
                "files": file_names
            }
        
        return {
            "analysis_id": analysis_id,
            "files_processed": len(files),
            "file_names": file_names,
            "status": "completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

@app.get("/api/summary/overall/{analysis_id}")
async def get_overall_summary(analysis_id: str):
    """Get overall financial summary with top categories and date range"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        # Get overall summary
        overall_summary = analyzer.overall_summary
        
        # Ensure it's in the correct format
        if overall_summary is None or 'Total Spends (Debits)' not in overall_summary:
            overall_summary = DataTransformer.ensure_standard_format(analyzer)
        
        overall_summary = convert_numpy_types(overall_summary)
        
        # Get top spending and earning categories
        top_spending_categories = []
        top_earning_categories = []
        
        if analyzer.category_summary is not None and not analyzer.category_summary.empty:
            df = analyzer.category_summary
            
            spending_list = []
            earning_list = []
            
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
        date_range = {"start_date": None, "end_date": None}
        if analyzer.categorized_df is not None and not analyzer.categorized_df.empty:
            if 'Txn Date' in analyzer.categorized_df.columns:
                dates = pd.to_datetime(analyzer.categorized_df['Txn Date'], errors='coerce')
                date_range = {
                    "start_date": dates.min().strftime('%Y-%m-%d') if not dates.isna().all() else None,
                    "end_date": dates.max().strftime('%Y-%m-%d') if not dates.isna().all() else None
                }
        
        return {
            "analysis_id": analysis_id,
            "overall_summary": overall_summary,
            "top_spending_categories": top_spending_categories,
            "top_earning_categories": top_earning_categories,
            "date_range": date_range,
            "filter_info": {"applied": "All Data"}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary/categories/{analysis_id}")
async def get_category_summary(analysis_id: str):
    """Get detailed category-wise summary"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        if analyzer.category_summary is None or analyzer.category_summary.empty:
            category_summary = {"category_summary": []}
        else:
            df = analyzer.category_summary
            categories_list = []
            
            for category in df.index:
                debit_amount = float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0
                credit_amount = float(df.loc[category, 'Total Credit']) if 'Total Credit' in df.columns else 0.0
                debit_count = int(df.loc[category, 'Debit Count']) if 'Debit Count' in df.columns else 0
                credit_count = int(df.loc[category, 'Credit Count']) if 'Credit Count' in df.columns else 0
                net_amount = credit_amount - debit_amount
                
                # Determine transaction type
                if debit_amount > 0 and credit_amount > 0:
                    transaction_type = "Mixed"
                elif credit_amount > 0:
                    transaction_type = "Income"
                elif 'transfer' in str(category).lower() or 'self' in str(category).lower():
                    transaction_type = "Transfer"
                elif 'atm' in str(category).lower() or 'cash' in str(category).lower():
                    transaction_type = "Cash Withdrawal"
                else:
                    transaction_type = "Expense"
                
                categories_list.append({
                    "Category": str(category),
                    "Total Debit": debit_amount,
                    "Debit Count": debit_count,
                    "Total Credit": credit_amount,
                    "Credit Count": credit_count,
                    "Net Amount": net_amount,
                    "Transaction Type": transaction_type
                })
            
            category_summary = {"category_summary": categories_list}
        
        return {
            "analysis_id": analysis_id,
            "category_summary": category_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/portfolio/{analysis_id}")
async def get_portfolio_analysis(analysis_id: str):
    """Get portfolio-specific analysis with external flows breakdown"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analysis_data = analysis_storage[analysis_id]
        
        # Use stored portfolio summary if available
        if "portfolio_summary" in analysis_data and analysis_data["portfolio_summary"]:
            portfolio_summary = analysis_data["portfolio_summary"]
            analyzer = analysis_data["analyzer"]
            
            # Get external inflows and outflows breakdown
            external_inflows_breakdown = []
            external_outflows_breakdown = []
            
            if analyzer and hasattr(analyzer, 'category_summary') and analyzer.category_summary is not None:
                df = analyzer.category_summary
                
                # Calculate total external amounts for percentages
                total_inflows = portfolio_summary.get("external_inflows", 0)
                total_outflows = portfolio_summary.get("external_outflows", 0)
                
                # Get top inflow and outflow categories
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
                        inflow_categories.append({
                            "category": str(category),
                            "amount": credit_amount,
                            "count": credit_count,
                            "percentage": round((credit_amount / total_inflows * 100), 1) if total_inflows > 0 else 0
                        })
                    
                    if debit_amount > 0:
                        outflow_categories.append({
                            "category": str(category),
                            "amount": debit_amount,
                            "count": debit_count,
                            "percentage": round((debit_amount / total_outflows * 100), 1) if total_outflows > 0 else 0
                        })
                
                # Sort and take top categories
                external_inflows_breakdown = sorted(inflow_categories, key=lambda x: x['amount'], reverse=True)[:5]
                external_outflows_breakdown = sorted(outflow_categories, key=lambda x: x['amount'], reverse=True)[:5]
            
            portfolio_insights = {
                "summary": {
                    "total_transactions": portfolio_summary.get("total_transactions", 0),
                    "external_transactions": portfolio_summary.get("external_transactions", 0),
                    "self_transfers_ignored": portfolio_summary.get("self_transfers_ignored", portfolio_summary.get("self_transfer_transactions", 0)),
                    "external_inflows": portfolio_summary.get("external_inflows", 0),
                    "external_outflows": portfolio_summary.get("external_outflows", 0),
                    "net_portfolio_change": portfolio_summary.get("net_portfolio_change", portfolio_summary.get("net_external_change", 0))
                },
                "external_inflows_breakdown": external_inflows_breakdown,
                "external_outflows_breakdown": external_outflows_breakdown,
                "analysis_type": "portfolio",
                "note": "Self-transfer transactions are completely ignored in portfolio analysis"
            }
            
            return {
                "analysis_id": analysis_id,
                "portfolio_insights": convert_numpy_types(portfolio_insights)
            }
        
        # Fallback for non-portfolio analysis
        analyzer = analysis_data["analyzer"]
        
        if not analyzer or not hasattr(analyzer, 'categorized_df') or analyzer.categorized_df is None:
            portfolio_insights = {
                "summary": {
                    "total_transactions": 0,
                    "external_transactions": 0,
                    "self_transfers_ignored": 0,
                    "external_inflows": 0,
                    "external_outflows": 0,
                    "net_portfolio_change": 0
                },
                "external_inflows_breakdown": [],
                "external_outflows_breakdown": [],
                "analysis_type": "portfolio",
                "note": "No portfolio data available"
            }
        else:
            # Basic portfolio calculation
            df = analyzer.categorized_df
            self_transfers = df[df['Category'].str.contains('Self Transfer', na=False)]
            external_transactions = df[~df['Category'].str.contains('Self Transfer', na=False)]
            
            total_transactions = len(df)
            external_count = len(external_transactions)
            self_transfer_count = len(self_transfers)
            
            external_inflows = external_transactions['Credit'].sum() if 'Credit' in external_transactions.columns else 0
            external_outflows = external_transactions['Debit'].sum() if 'Debit' in external_transactions.columns else 0
            net_portfolio_change = external_inflows - external_outflows
            
            portfolio_insights = {
                "summary": {
                    "total_transactions": int(total_transactions),
                    "external_transactions": int(external_count),
                    "self_transfers_ignored": int(self_transfer_count),
                    "external_inflows": float(external_inflows),
                    "external_outflows": float(external_outflows),
                    "net_portfolio_change": float(net_portfolio_change)
                },
                "external_inflows_breakdown": [],
                "external_outflows_breakdown": [],
                "analysis_type": "portfolio",
                "note": "Self-transfer transactions are completely ignored in portfolio analysis"
            }
        
        return {
            "analysis_id": analysis_id,
            "portfolio_insights": convert_numpy_types(portfolio_insights)
        }
        
    except Exception as e:
        return {
            "analysis_id": analysis_id,
            "portfolio_insights": {
                "summary": {
                    "total_transactions": 0,
                    "external_transactions": 0,
                    "self_transfers_ignored": 0,
                    "external_inflows": 0,
                    "external_outflows": 0,
                    "net_portfolio_change": 0
                },
                "external_inflows_breakdown": [],
                "external_outflows_breakdown": [],
                "analysis_type": "portfolio",
                "note": f"Error: {str(e)}"
            }
        }

@app.get("/api/analysis/upi/{analysis_id}")
async def get_upi_analysis(analysis_id: str):
    """Get UPI-specific analysis with hierarchy"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        if not analyzer or not hasattr(analyzer, 'categorized_df') or analyzer.categorized_df is None:
            return {
                "analysis_id": analysis_id,
                "upi_analysis": {
                    "summary": {
                        "total_upi_transactions": 0,
                        "total_upi_debit": 0,
                        "total_upi_credit": 0,
                        "net_upi_amount": 0
                    },
                    "upi_spending_categories": [],
                    "upi_hierarchy": {}
                }
            }
        
        df = analyzer.categorized_df
        
        # Filter UPI transactions
        upi_transactions = df[df['Category'].str.contains('UPI', na=False, case=False)]
        
        if upi_transactions.empty:
            return {
                "analysis_id": analysis_id,
                "upi_analysis": {
                    "summary": {
                        "total_upi_transactions": 0,
                        "total_upi_debit": 0,
                        "total_upi_credit": 0,
                        "net_upi_amount": 0
                    },
                    "upi_spending_categories": [],
                    "upi_hierarchy": {}
                }
            }
        
        # Calculate UPI summary
        total_upi_debit = upi_transactions['Debit'].sum() if 'Debit' in upi_transactions.columns else 0
        total_upi_credit = upi_transactions['Credit'].sum() if 'Credit' in upi_transactions.columns else 0
        
        upi_summary = {
            "total_upi_transactions": len(upi_transactions),
            "total_upi_debit": float(total_upi_debit),
            "total_upi_credit": float(total_upi_credit),
            "net_upi_amount": float(total_upi_credit - total_upi_debit)
        }
        
        # Get UPI categories
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
                    
                    upi_categories.append({
                        "category": str(category),
                        "total_debit": debit_amount,
                        "debit_count": debit_count,
                        "total_credit": credit_amount,
                        "credit_count": credit_count,
                        "net_amount": credit_amount - debit_amount
                    })
                    
                    # Build hierarchy
                    parts = str(category).split('-')
                    if len(parts) >= 3:  # UPI-MainCategory-SubCategory
                        main_cat = parts[1]
                        sub_cat = parts[2] if len(parts) > 2 else "Other"
                        
                        if main_cat not in upi_hierarchy:
                            upi_hierarchy[main_cat] = {
                                "total_debit": 0,
                                "total_credit": 0,
                                "net_amount": 0,
                                "subcategories": {}
                            }
                        
                        upi_hierarchy[main_cat]["total_debit"] += debit_amount
                        upi_hierarchy[main_cat]["total_credit"] += credit_amount
                        upi_hierarchy[main_cat]["net_amount"] += (credit_amount - debit_amount)
                        
                        upi_hierarchy[main_cat]["subcategories"][sub_cat] = {
                            "debit": debit_amount,
                            "credit": credit_amount,
                            "count": debit_count + credit_count
                        }
        
        return {
            "analysis_id": analysis_id,
            "upi_analysis": {
                "summary": upi_summary,
                "upi_spending_categories": upi_categories,
                "upi_hierarchy": upi_hierarchy
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/{analysis_id}")
async def get_transactions(analysis_id: str):
    """Get transaction list (first 100 transactions)"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        if not analyzer or not hasattr(analyzer, 'categorized_df') or analyzer.categorized_df is None:
            return {
                "analysis_id": analysis_id,
                "transactions": [],
                "total_shown": 0,
                "summary": {
                    "total_debits_shown": 0,
                    "total_credits_shown": 0,
                    "net_amount_shown": 0
                },
                "note": "No transaction data available"
            }
        
        df = analyzer.categorized_df
        
        if df.empty:
            return {
                "analysis_id": analysis_id,
                "transactions": [],
                "total_shown": 0,
                "summary": {
                    "total_debits_shown": 0,
                    "total_credits_shown": 0,
                    "net_amount_shown": 0
                },
                "note": "No transactions found"
            }
        
        # Get first 100 transactions
        transactions_subset = df.head(100)
        transactions_list = []
        
        for _, row in transactions_subset.iterrows():
            transaction = {
                "Date": str(row.get('Txn Date', '')),
                "Description": str(row.get('Description', '')),
                "Amount": float(row.get('Amount', 0)),
                "Category": str(row.get('Category', '')),
                "Reference": str(row.get('Reference', '')),
                "Balance": float(row.get('Balance', 0)),
                "Debit": float(row.get('Debit', 0)),
                "Credit": float(row.get('Credit', 0)),
                "Transaction_Type": "Credit" if row.get('Credit', 0) > 0 else "Debit",
                "Source_File": str(row.get('Source_File', '')),
                "Bank": str(row.get('Bank', '')),
                "Year": int(row.get('Year', 0)) if pd.notna(row.get('Year', 0)) else 0
            }
            transactions_list.append(transaction)
        
        # Calculate summary for shown transactions
        total_debits_shown = transactions_subset['Debit'].sum() if 'Debit' in transactions_subset.columns else 0
        total_credits_shown = transactions_subset['Credit'].sum() if 'Credit' in transactions_subset.columns else 0
        
        return {
            "analysis_id": analysis_id,
            "transactions": transactions_list,
            "total_shown": len(transactions_list),
            "summary": {
                "total_debits_shown": float(total_debits_shown),
                "total_credits_shown": float(total_credits_shown),
                "net_amount_shown": float(total_credits_shown - total_debits_shown)
            },
            "note": f"Showing first {len(transactions_list)} transactions"
        }
        
    except Exception as e:
        return {
            "analysis_id": analysis_id,
            "transactions": [],
            "total_shown": 0,
            "summary": {
                "total_debits_shown": 0,
                "total_credits_shown": 0,
                "net_amount_shown": 0
            },
            "note": f"Error: {str(e)}"
        }

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
