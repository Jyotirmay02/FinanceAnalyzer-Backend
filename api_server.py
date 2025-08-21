"""
FinanceAnalyzer Backend API Server
FastAPI server providing REST APIs for financial analysis
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
import tempfile
import uuid
from typing import Optional, Dict, Any, List
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.finance_analyzer import FinanceAnalyzer
from src.multi_file_analyzer import process_multiple_files
from src.portfolio_analyzer import process_portfolio_files
from src.data_transformer import DataTransformer

app = FastAPI(
    title="FinanceAnalyzer API",
    description="Backend API for financial transaction analysis",
    version="1.0.0"
)

# CORS middleware
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
    """Convert numpy types to native Python types"""
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

@app.get("/")
async def root():
    """Health check"""
    return {"message": "FinanceAnalyzer API is running", "version": "1.0.0"}

@app.post("/api/analyze")
async def analyze_files(
    files: List[UploadFile] = File(...),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    Analyze single or multiple financial files
    """
    # Validate file count
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed")
    
    # Validate files
    temp_files = []
    try:
        for file in files:
            if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
            
            content = await file.read()
            if len(content) > 1024 * 1024:  # 1MB limit
                raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
            
            # Save temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
            temp_file.write(content)
            temp_file.close()
            temp_files.append(temp_file.name)
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Perform analysis
        if len(temp_files) == 1:
            # Single file analysis
            analyzer = FinanceAnalyzer(temp_files[0], from_date=from_date, to_date=to_date)
            output_file = analyzer.run_full_analysis()
            
            # Store results
            analysis_storage[analysis_id] = {
                "type": "single",
                "analyzer": analyzer,
                "output_file": output_file,
                "files": [files[0].filename]
            }
        else:
            # Multi-file analysis - use individual files and combine results
            analyzers = []
            all_transactions = []
            
            for temp_file in temp_files:
                try:
                    # Process each file individually
                    analyzer = FinanceAnalyzer(temp_file, from_date=from_date, to_date=to_date)
                    analyzer.run_full_analysis()
                    analyzers.append(analyzer)
                    
                    # Collect transactions
                    if analyzer.categorized_df is not None:
                        all_transactions.append(analyzer.categorized_df)
                except Exception as e:
                    print(f"Error processing {temp_file}: {e}")
                    continue
            
            if not analyzers:
                raise HTTPException(status_code=400, detail="Failed to process any files")
            
            # Combine all transactions
            if all_transactions:
                combined_df = pd.concat(all_transactions, ignore_index=True)
                combined_df = combined_df.sort_values('Txn Date') if 'Txn Date' in combined_df.columns else combined_df
                
                # Create a combined analyzer with proper summaries
                main_analyzer = analyzers[0]  # Use first analyzer as base
                main_analyzer.categorized_df = combined_df
                main_analyzer.generate_summaries()  # Regenerate summaries with combined data
                
                analyzer = main_analyzer
            else:
                analyzer = analyzers[0]  # Fallback to first analyzer
            
            analysis_storage[analysis_id] = {
                "type": "multi",
                "analyzer": analyzer,
                "output_file": None,
                "files": [f.filename for f in files]
            }
        
        return {
            "analysis_id": analysis_id,
            "files_processed": len(files),
            "file_names": [f.filename for f in files],
            "status": "completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

@app.get("/api/transactions/{analysis_id}")
async def get_transactions(analysis_id: str):
    """Get first 100 transactions for an analysis"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        # Check if analyzer and data exist
        if not analyzer or not hasattr(analyzer, 'categorized_df') or analyzer.categorized_df is None:
            return {
                "analysis_id": analysis_id,
                "transactions": [],
                "total_shown": 0,
                "error": "No transaction data available"
            }
        
        # Get categorized transactions (first 100)
        transactions = analyzer.categorized_df.head(100)
        
        if transactions.empty:
            return {
                "analysis_id": analysis_id,
                "transactions": [],
                "total_shown": 0,
                "error": "No transactions found"
            }
        
        # Normalize field names for frontend compatibility
        transactions_list = []
        for _, row in transactions.iterrows():
            transaction = {
                "Date": str(row.get("Txn Date", row.get("Date", ""))),
                "Description": str(row.get("Description", "")),
                "Amount": float(row.get("Credit", 0) - row.get("Debit", 0)) if "Credit" in row and "Debit" in row else float(row.get("Amount", 0)),
                "Category": str(row.get("Category", "")),
                "Reference": str(row.get("Reference", "")),
                "Balance": float(row.get("Balance", 0)),
                "Debit": float(row.get("Debit", 0)),
                "Credit": float(row.get("Credit", 0))
            }
            transactions_list.append(transaction)
        
        return {
            "analysis_id": analysis_id,
            "transactions": transactions_list,
            "total_shown": len(transactions_list),
            "note": "Showing first 100 transactions"
        }
        
    except Exception as e:
        return {
            "analysis_id": analysis_id,
            "transactions": [],
            "total_shown": 0,
            "error": f"Failed to load transactions: {str(e)}"
        }

@app.get("/api/summary/categories/{analysis_id}")
async def get_category_summary(analysis_id: str):
    """Get category-wise spending summary"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        # Get category summary
        category_summary = analyzer.category_summary
        
        # Convert DataFrame to list format expected by frontend
        if hasattr(category_summary, 'to_dict'):
            # Convert DataFrame to list of dictionaries
            category_list = []
            df = category_summary
            for category in df.index:
                category_list.append({
                    'Category': str(category),
                    'Total Debit': float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0,
                    'Debit Count': int(df.loc[category, 'Debit Count']) if 'Debit Count' in df.columns else 0,
                    'Total Credit': float(df.loc[category, 'Total Credit']) if 'Total Credit' in df.columns else 0.0,
                    'Credit Count': int(df.loc[category, 'Credit Count']) if 'Credit Count' in df.columns else 0
                })
            category_summary = {"category_summary": category_list}
        else:
            category_summary = {"category_summary": []}
        
        return {
            "analysis_id": analysis_id,
            "category_summary": category_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary/overall/{analysis_id}")
async def get_overall_summary(analysis_id: str):
    """Get overall financial summary"""
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
        
        # Get top categories for dashboard
        top_categories = []
        if analyzer.category_summary is not None and not analyzer.category_summary.empty:
            # Convert DataFrame to list format
            df = analyzer.category_summary
            categories_list = []
            for category in df.index:
                debit_amount = float(df.loc[category, 'Total Debit']) if 'Total Debit' in df.columns else 0.0
                if debit_amount > 0:  # Only spending categories
                    categories_list.append({
                        'Category': str(category),
                        'Total Debit': debit_amount
                    })
            
            # Sort by amount and take top 5
            top_categories = sorted(categories_list, key=lambda x: x['Total Debit'], reverse=True)[:5]
        
        return {
            "analysis_id": analysis_id,
            "overall_summary": overall_summary,
            "top_categories": top_categories or [],
            "filter_info": {"applied": "All Data"}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/upi/{analysis_id}")
async def get_upi_analysis(analysis_id: str):
    """Get UPI-specific analysis"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        analyzer = analysis_storage[analysis_id]["analyzer"]
        
        # Get UPI analysis
        upi_analysis = {
            "upi_categories": {},
            "total_upi_transactions": 0,
            "total_upi_debit": 0,
            "upi_hierarchy": {}
        }
        
        if analyzer.categorized_df is not None and not analyzer.categorized_df.empty:
            # Filter UPI transactions
            upi_transactions = analyzer.categorized_df[
                analyzer.categorized_df['Description'].str.contains('UPI', case=False, na=False) |
                analyzer.categorized_df['Category'].str.contains('UPI', case=False, na=False)
            ]
            
            if not upi_transactions.empty:
                upi_analysis["total_upi_transactions"] = len(upi_transactions)
                upi_analysis["total_upi_debit"] = float(upi_transactions['Debit'].sum()) if 'Debit' in upi_transactions.columns else 0
                
                # Create hierarchy by category
                hierarchy = {}
                for _, row in upi_transactions.iterrows():
                    category = row.get('Category', 'Others')
                    debit = float(row.get('Debit', 0))
                    
                    if category not in hierarchy:
                        hierarchy[category] = {
                            'total_debit': 0,
                            'subcategories': {}
                        }
                    
                    hierarchy[category]['total_debit'] += debit
                    
                    # Use description as subcategory
                    desc = str(row.get('Description', 'Unknown'))[:50]
                    if desc not in hierarchy[category]['subcategories']:
                        hierarchy[category]['subcategories'][desc] = {
                            'count': 0,
                            'total_debit': 0
                        }
                    
                    hierarchy[category]['subcategories'][desc]['count'] += 1
                    hierarchy[category]['subcategories'][desc]['total_debit'] += debit
                
                upi_analysis["upi_hierarchy"] = hierarchy
        
        return {
            "analysis_id": analysis_id,
            "upi_analysis": upi_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/{analysis_id}")
async def export_analysis(analysis_id: str, format: str = "excel"):
    """Export analysis results (summaries only)"""
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if format not in ["excel", "csv"]:
        raise HTTPException(status_code=400, detail="Format must be 'excel' or 'csv'")
    
    try:
        output_file = analysis_storage[analysis_id]["output_file"]
        
        if format == "excel":
            return FileResponse(
                output_file,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"analysis_{analysis_id}.xlsx"
            )
        else:
            # Convert to CSV (summary only)
            analyzer = analysis_storage[analysis_id]["analyzer"]
            summary_df = pd.DataFrame([analyzer.overall_summary])
            
            csv_file = f"/tmp/analysis_{analysis_id}.csv"
            summary_df.to_csv(csv_file, index=False)
            
            return FileResponse(
                csv_file,
                media_type="text/csv",
                filename=f"analysis_{analysis_id}.csv"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
