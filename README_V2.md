# FinanceAnalyzer Backend API v2

A comprehensive REST API server for personal finance analysis with Mint-like frontend support.

## 🚀 Features

- **File Upload & Analysis**: Process multiple bank statement files (CSV/Excel)
- **Dashboard API**: Overall summary with top categories and recent transactions
- **Categories Analysis**: Detailed spending and income category breakdowns
- **Transaction Management**: Paginated transaction lists with filtering
- **UPI Analysis**: Specialized UPI transaction analysis
- **Proper Data Models**: Pydantic models with validation and documentation
- **Error Handling**: Structured error responses with proper HTTP codes
- **CORS Support**: Ready for frontend integration

## 📋 Requirements

```
fastapi>=0.104.0
uvicorn>=0.24.0
pandas>=2.0.0
openpyxl>=3.1.0
pydantic>=2.0.0
python-multipart>=0.0.6
```

## 🛠️ Installation

```bash
# Clone the repository
git checkout mint

# Install dependencies
pip install -r requirements.txt

# Run the server
python api_v2_server.py
```

The server will start on `http://localhost:8001`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### API Contract
See [API_V2_CONTRACT.md](API_V2_CONTRACT.md) for detailed endpoint documentation.

## 🏗️ Architecture

```
src/
├── api_v2_models.py          # Pydantic models for v2 API
├── api_v2_transformers.py    # Data transformation logic
├── excel_models.py           # Backend data models
├── finance_analyzer.py       # Core analysis engine
├── data_transformer.py       # Data processing
└── ...

api_v2_server.py             # FastAPI application
API_V2_CONTRACT.md           # API documentation
```

## 🔄 Data Flow

1. **File Upload** → Files processed by `FinanceAnalyzer`
2. **Analysis** → Data transformed to `PortfolioAnalysisData`
3. **Storage** → Results stored in memory with unique `analysis_id`
4. **API Calls** → Data transformed to v2 models via `APIv2Transformer`
5. **Response** → Structured JSON responses to frontend

## 📊 Data Models

### Core Models

#### CategorySummaryV2
```python
{
    "category": str,
    "total_debit": float,
    "debit_count": int,
    "total_credit": float,
    "credit_count": int,
    "net_amount": float,
    "percentage": float
}
```

#### TransactionV2
```python
{
    "id": str,
    "date": str,  # YYYY-MM-DD
    "description": str,
    "amount": float,  # Positive for credit, negative for debit
    "category": str,
    "bank": str,
    "balance": float,
    "transaction_type": "debit" | "credit",
    "source_file": str
}
```

#### OverallSummaryV2
```python
{
    "total_earned": float,
    "total_spent": float,
    "net_change": float,
    "total_transactions": int,
    "date_range_start": str,
    "date_range_end": str
}
```

## 🌐 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v2/analyze` | Upload and analyze files |
| `GET` | `/api/v2/dashboard/{analysis_id}` | Dashboard data |
| `GET` | `/api/v2/categories/{analysis_id}` | Categories analysis |
| `GET` | `/api/v2/transactions/{analysis_id}` | Paginated transactions |
| `GET` | `/api/v2/upi-analysis/{analysis_id}` | UPI analysis |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v2/analysis/{analysis_id}/info` | Analysis information |
| `GET` | `/api/v2/analysis` | List all analyses |
| `GET` | `/` | Health check |

## 🔧 Usage Examples

### 1. Upload Files
```bash
curl -X POST "http://localhost:8001/api/v2/analyze" \
  -F "files=@hdfc_statement.csv" \
  -F "files=@icici_statement.xlsx"
```

### 2. Get Dashboard Data
```bash
curl "http://localhost:8001/api/v2/dashboard/{analysis_id}"
```

### 3. Get Categories
```bash
curl "http://localhost:8001/api/v2/categories/{analysis_id}"
```

### 4. Get Transactions with Pagination
```bash
curl "http://localhost:8001/api/v2/transactions/{analysis_id}?page=1&page_size=20&category=Food"
```

## 🎯 Frontend Integration

### React Service Class
```javascript
class FinanceAPIService {
  constructor(baseURL = 'http://localhost:8001') {
    this.baseURL = baseURL;
  }

  async uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const response = await fetch(`${this.baseURL}/api/v2/analyze`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  }

  async getDashboard(analysisId) {
    const response = await fetch(`${this.baseURL}/api/v2/dashboard/${analysisId}`);
    return response.json();
  }

  async getCategories(analysisId) {
    const response = await fetch(`${this.baseURL}/api/v2/categories/${analysisId}`);
    return response.json();
  }
}
```

### Frontend Data Mapping

| Frontend Component | API Endpoint | Data Used |
|-------------------|--------------|-----------|
| Dashboard Overview | `/api/v2/dashboard/{id}` | `overall_summary` |
| Categories Page | `/api/v2/categories/{id}` | `spending_categories`, `income_categories` |
| Transactions Page | `/api/v2/transactions/{id}` | `transactions` with pagination |
| UPI Analysis Page | `/api/v2/upi-analysis/{id}` | `upi_categories` |

## 🧪 Testing

### Run Tests
```bash
# Start server
python api_v2_server.py

# Test endpoints
curl http://localhost:8001/
curl -X POST http://localhost:8001/api/v2/analyze -F "files=@test_statement.csv"
```

### Sample Data
Use the sample Excel file `complete_portfolio_analysis1.xlsx` for testing:
- 368 transactions across 43 categories
- UPI analysis with 17 categories
- Date range: Multiple years of data

## 🚨 Error Handling

### Error Response Format
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "additional": "context"
  }
}
```

### Common Error Codes
- `HTTP_400`: Bad Request
- `HTTP_404`: Analysis not found
- `HTTP_422`: Validation error
- `HTTP_500`: Internal server error

## 🔒 Security Considerations

### Current Implementation (Development)
- No authentication required
- CORS enabled for localhost
- File uploads stored temporarily
- In-memory data storage

### Production Recommendations
- Add JWT authentication
- Implement rate limiting
- Use persistent storage (Redis/Database)
- Add file validation and virus scanning
- Enable HTTPS only
- Restrict CORS origins

## 📈 Performance

### Current Limitations
- In-memory storage (limited by RAM)
- No caching layer
- Synchronous file processing

### Optimization Opportunities
- Add Redis for caching
- Implement async file processing
- Add database persistence
- Implement pagination for large datasets

## 🔄 Migration from v1

### Key Changes
- Structured data models instead of dictionaries
- Consistent naming conventions (snake_case)
- Proper error handling with HTTP codes
- Pagination support for large datasets
- Filtering and search capabilities

### Breaking Changes
- All endpoints now under `/api/v2/` prefix
- Response format changed to structured models
- Transaction amounts: positive for credits, negative for debits
- Date format standardized to YYYY-MM-DD

## 🤝 Contributing

1. Create feature branch from `mint`
2. Follow existing code structure
3. Add proper type hints and documentation
4. Update API contract documentation
5. Test with frontend integration

## 📝 License

This project is for personal use and development purposes.

---

**API Version**: 2.0.0  
**Last Updated**: August 2024  
**Compatibility**: React Frontend v1.0+
