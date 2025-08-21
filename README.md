# FinanceAnalyzer Backend

A comprehensive financial analysis tool that processes bank statements and provides detailed insights through both CLI and web API interfaces.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Poetry (recommended for dependency management)

### Installation & Setup

```bash
# Clone the repository
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Backend.git
cd FinanceAnalyzer-Backend

# Install dependencies using Poetry (recommended)
poetry install

# Alternative: Using pip
pip install -r requirements.txt
```

## 🖥️ Running the Servers

### Method 1: Using Poetry (Recommended)
```bash
cd FinanceAnalyzer-Backend
poetry run python start_server.py
```

### Method 2: Direct Python
```bash
cd FinanceAnalyzer-Backend
python start_server.py
```

### Method 3: Using uvicorn directly
```bash
cd FinanceAnalyzer-Backend
poetry run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
# Or without Poetry:
# uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Server Verification
- **API Base**: http://localhost:8000
- **Health Check**: http://localhost:8000/ → `{"message": "FinanceAnalyzer API is running"}`
- **API Documentation**: http://localhost:8000/docs (Interactive Swagger UI)
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📊 Usage

### Web API Server

The FastAPI server provides REST endpoints for the frontend:

```bash
# Start server
python start_server.py

# Server logs will show:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### CLI Analysis

Run financial analysis directly from command line:

```bash
# Test CLI functionality
python cli_runner.py

# Expected output:
# ✅ CLI test successful!
# 📊 Generated: visuals/financial_analysis.xlsx
# 📄 Excel file size: 20,472 bytes
```

### Supported File Formats

- **Excel files**: `.xls`, `.xlsx` (SBI format)
- **CSV files**: Bank statement exports
- **Multiple banks**: SBI, ICICI, HDFC (auto-detected)

## 🔌 API Endpoints

### File Upload & Analysis
```http
POST /api/analyze
Content-Type: multipart/form-data

# Single file upload
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@path/to/statement.xls"

# Multi-file upload
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@statement1.xls" \
  -F "files=@statement2.csv"

# With date filters
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@statement.xls" \
  -F "from_date=01-2024" \
  -F "to_date=12-2024"

# Response: {"analysis_id": "uuid", "files_processed": 1, "status": "completed"}
```

### Data Retrieval
```http
# Get overall financial summary
GET /api/summary/overall/{analysis_id}

# Get category-wise breakdown
GET /api/summary/categories/{analysis_id}

# Get UPI transaction analysis
GET /api/analysis/upi/{analysis_id}

# Get transaction list (first 100)
GET /api/transactions/{analysis_id}

# Export data as CSV
GET /api/export/{analysis_id}?format=csv
```

### Example API Usage
```bash
# 1. Upload file
ANALYSIS_ID=$(curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@SBI_2024.xls" | jq -r '.analysis_id')

# 2. Get dashboard data
curl "http://localhost:8000/api/summary/overall/$ANALYSIS_ID"

# 3. Get UPI analysis
curl "http://localhost:8000/api/analysis/upi/$ANALYSIS_ID"
```

## 📈 Features

### Financial Analysis
- **Transaction Processing**: Automatic categorization of expenses
- **UPI Analysis**: Detailed breakdown of UPI transactions
- **Category Summaries**: Spending patterns by category
- **Time-based Filtering**: Monthly, yearly, date range analysis
- **Multi-file Support**: Analyze multiple bank statements together

### Output Formats
- **Excel Reports**: Comprehensive analysis with multiple sheets
- **JSON API**: Structured data for web applications
- **Console Output**: Quick summary for CLI usage
- **CSV Export**: Data export for external analysis

### Bank Support
- **SBI**: State Bank of India statements
- **ICICI**: ICICI Bank statements  
- **HDFC**: HDFC Bank statements
- **Generic CSV**: Standard bank export formats

## 🏗️ Architecture

```
├── api_server.py           # FastAPI web server (main entry point)
├── start_server.py         # Server startup script
├── cli_runner.py          # CLI testing utility
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Poetry configuration
└── src/
    ├── finance_analyzer.py     # Main analysis engine
    ├── data_loader.py         # File parsing and loading
    ├── transaction_processor.py # Transaction categorization
    ├── upi_categorizer.py     # UPI-specific analysis
    ├── excel_writer.py        # Excel report generation
    ├── multi_file_analyzer.py # Multi-file processing
    └── cli.py                 # Command line interface
```

## 📊 Sample Output

### API Response Example
```json
{
  "analysis_id": "uuid-here",
  "overall_summary": {
    "Total Spends (Debits)": 6769504.92,
    "Total Credits": 7482825.00,
    "Net Change": 713320.08,
    "Total Transactions": 150
  },
  "top_categories": [
    {"Category": "Self Canara", "Total Debit": 2435000.00},
    {"Category": "Cheq", "Total Debit": 1656950.00}
  ],
  "filter_info": {
    "date_range": "2024-01-01 to 2024-12-31",
    "total_files": 1
  }
}
```

### Console Summary
```
==================================================
FINANCIAL ANALYSIS SUMMARY
==================================================
Filter Applied: All Data

Total Spends: ₹6,769,504.92
Total Credits: ₹7,482,825.00
Net Change: ₹713,320.08
Total Transactions: 150

Top 5 Spending Categories:
  Self Canara: ₹2,435,000.00
  Cheq: ₹1,656,950.00
  Gangadhar Hardware: ₹834,487.60
  Loan Account 1: ₹534,530.00
  Mantu-Plot: ₹300,012.00
==================================================
```

## 🧪 Testing

### API Testing
```bash
# Start server
python start_server.py

# Test health endpoint
curl http://localhost:8000/

# Test file upload
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@../FinanceAnalyzer/data/SBI_2024.xls"

# Test with sample data
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@../FinanceAnalyzer/data/1754580321215.CSV"
```

### CLI Testing
```bash
# Test CLI functionality using Poetry (recommended)
poetry run python cli_runner.py

# Or without Poetry
python cli_runner.py

# Expected output:
# 🧪 Testing CLI Functionality
# ✅ CLI test successful!
# 📊 Generated: visuals/financial_analysis.xlsx
# 📄 Excel file size: 20,472 bytes
```

### Load Testing
```bash
# Test multiple concurrent uploads
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/analyze" \
    -F "files=@../FinanceAnalyzer/data/SBI_2024.xls" &
done
wait
```

## 🔧 Development

### Project Structure
- `api_server.py`: FastAPI application with all endpoints
- `start_server.py`: Server startup with configuration
- `src/`: Core analysis modules
- `visuals/`: Generated Excel reports
- `cli_runner.py`: CLI testing utility

### Adding New Banks
1. Add bank detection logic in `data_loader.py`
2. Implement parsing in `transaction_processor.py`
3. Update categorization rules in `upi_categorizer.py`
4. Test with sample data

### Configuration
```python
# api_server.py configuration
HOST = "0.0.0.0"
PORT = 8000
CORS_ORIGINS = ["http://localhost:3000"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## 🚨 Troubleshooting

### Server Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
kill -9 $(lsof -t -i:8000)

# Try different port
uvicorn api_server:app --port 8001
```

### Import Errors
```bash
# Ensure you're in the correct directory
cd FinanceAnalyzer-Backend

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt
```

### File Upload Issues
```bash
# Check file permissions
ls -la ../FinanceAnalyzer/data/

# Verify file format
file ../FinanceAnalyzer/data/SBI_2024.xls

# Check server logs for detailed errors
python start_server.py  # Watch console output
```

### Memory Issues
```bash
# Monitor memory usage
top -p $(pgrep -f "python.*api_server")

# Increase memory limits if needed
ulimit -v 2097152  # 2GB virtual memory limit
```

## 📊 Performance

### Benchmarks
- **Single file (150 transactions)**: ~2-3 seconds
- **Multi-file (1000+ transactions)**: ~5-10 seconds
- **Memory usage**: ~50-100MB per analysis
- **Concurrent requests**: Up to 10 simultaneous uploads

### Optimization Tips
- Use SSD storage for temporary files
- Increase RAM for large file processing
- Enable gzip compression for API responses
- Use connection pooling for database operations

## 🔒 Security

### Current Measures
- File type validation (CSV, XLS, XLSX only)
- File size limits (10MB default)
- CORS configuration for frontend
- Input sanitization for date parameters

### Production Recommendations
- Add authentication/authorization
- Implement rate limiting
- Use HTTPS in production
- Add request logging and monitoring
- Validate file content, not just extensions

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs` endpoint
- Review the sample data in `../FinanceAnalyzer/data/` directory

---

**Quick Commands Summary:**
```bash
# Setup
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Backend.git
cd FinanceAnalyzer-Backend && pip install -r requirements.txt

# Run Server
python start_server.py  # API on :8000

# Test CLI
python cli_runner.py   # Generates Excel reports

# Test API
curl http://localhost:8000/  # Health check
curl -X POST "http://localhost:8000/api/analyze" -F "files=@data.xls"
```
