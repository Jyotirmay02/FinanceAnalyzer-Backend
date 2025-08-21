# FinanceAnalyzer Backend

A comprehensive financial analysis tool that processes bank statements and provides detailed insights through both CLI and web API interfaces.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Poetry (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Backend.git
cd FinanceAnalyzer-Backend

# Install dependencies using Poetry
poetry install

# Or using pip
pip install -r requirements.txt
```

## 📊 Usage

### Web API Server

Start the FastAPI server for web interface integration:

```bash
# Using Poetry
poetry run python start_server.py

# Or directly
python start_server.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

### CLI Analysis

Run financial analysis directly from command line:

```bash
# Basic analysis
python cli_runner.py

# The CLI will process data/SBI_2024.xls and generate:
# - visuals/financial_analysis.xlsx (comprehensive report)
# - Console summary with key metrics
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

# Upload bank statement file for analysis
# Returns: {"analysis_id": "uuid", "message": "success"}
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

### Bank Support
- **SBI**: State Bank of India statements
- **ICICI**: ICICI Bank statements  
- **HDFC**: HDFC Bank statements
- **Generic CSV**: Standard bank export formats

## 🏗️ Architecture

```
src/
├── finance_analyzer.py     # Main analysis engine
├── data_loader.py         # File parsing and loading
├── transaction_processor.py # Transaction categorization
├── upi_categorizer.py     # UPI-specific analysis
├── excel_writer.py        # Excel report generation
├── cli.py                 # Command line interface
└── api_server.py          # FastAPI web server
```

## 📊 Sample Output

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
  ]
}
```

## 🧪 Testing

### CLI Testing
```bash
# Test CLI functionality
python cli_runner.py

# Expected output:
# ✅ CLI test successful!
# 📊 Generated: visuals/financial_analysis.xlsx
# 📄 Excel file size: 20,472 bytes
```

### API Testing
```bash
# Start server
python start_server.py

# Test file upload (in another terminal)
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@../FinanceAnalyzer/data/SBI_2024.xls"

# Test data retrieval
curl "http://localhost:8000/api/summary/overall/{analysis_id}"
```

## 🔧 Development

### Project Structure
- `src/`: Core analysis modules
- `visuals/`: Generated Excel reports
- `api_server.py`: FastAPI web server
- `cli_runner.py`: CLI testing utility
- `start_server.py`: Server startup script

### Adding New Banks
1. Add bank detection logic in `data_loader.py`
2. Implement parsing in `transaction_processor.py`
3. Update categorization rules in `upi_categorizer.py`

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
