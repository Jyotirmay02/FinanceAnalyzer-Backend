# FinanceAnalyzer-Backend

Backend API server for FinanceAnalyzer with CLI compatibility.

## Features

- **REST API**: FastAPI-based backend with comprehensive financial analysis endpoints
- **CLI Compatibility**: All existing CLI commands continue to work unchanged
- **Multi-file Support**: Analyze single or multiple bank statement files
- **Multiple Formats**: Support for CSV, Excel (.xlsx, .xls) files
- **In-memory Storage**: Analysis results stored in memory (cleared on server restart)
- **Export Functionality**: Download analysis results as Excel or CSV

## API Endpoints

### Core Analysis
- `POST /api/analyze` - Upload and analyze files (max 20 files, 1MB each)
- `GET /api/transactions/{analysis_id}` - Get first 100 transactions
- `GET /api/summary/categories/{analysis_id}` - Category-wise spending summary
- `GET /api/summary/overall/{analysis_id}` - Overall financial summary
- `GET /api/analysis/upi/{analysis_id}` - UPI-specific analysis
- `GET /api/export/{analysis_id}` - Export analysis results

### Health Check
- `GET /` - API health check

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Poetry (for dependency management)

### 1. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
# OR
pip install poetry
```

### 2. Setup Virtual Environment & Install Dependencies
```bash
cd ~/Documents/Finance/FinanceAnalyzer-Backend

# Install dependencies in virtual environment
poetry install
```

### 3. Start the Server
```bash
# Option 1: Using Poetry (recommended)
poetry run python start_server.py

# Option 2: Direct uvicorn
poetry run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## CLI Usage (Unchanged)

All existing CLI functionality remains intact:

```bash
# Single file analysis
poetry run python src/cli.py --input ../FinanceAnalyzer/data/bank_statement.csv

# Multi-file analysis  
poetry run python src/multi_file_analyzer.py

# Portfolio analysis
poetry run python src/portfolio_analyzer.py
```

## Development

### Virtual Environment Management
```bash
# Run commands in virtual environment
poetry run <command>

# Install new dependency
poetry add package-name

# Install development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show virtual environment info
poetry env info
```

### Adding New Dependencies
```bash
# Add runtime dependency
poetry add fastapi uvicorn

# Add development dependency
poetry add --group dev pytest black isort
```

### Testing the API
```bash
# Make sure server is running, then test
curl http://localhost:8000/

# Upload file for analysis
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@../FinanceAnalyzer/data/sample.csv"
```

## Security Notes

- **Data Protection**: All financial data files are excluded from version control
- **Memory Storage**: Analysis results are stored in memory and cleared on server restart
- **File Limits**: 1MB per file, maximum 20 files per analysis
- **CORS**: Configured for localhost:3000 (frontend development)

## Author

**Jyotirmay Sethi**  
Email: jyotirmays123@gmail.com
