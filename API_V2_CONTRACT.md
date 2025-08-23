# FinanceAnalyzer API v2 Contract

## Overview
REST API for Mint-like personal finance frontend with proper data models and comprehensive endpoints.

**Base URL**: `http://localhost:8001`  
**API Version**: v2  
**Content-Type**: `application/json`

## Authentication
Currently no authentication required (development mode).

## Common Response Format

### Success Response
```json
{
  "data": { ... },
  "status": "success"
}
```

### Error Response
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

## Endpoints

### 1. Health Check
**GET** `/`

**Response:**
```json
{
  "message": "FinanceAnalyzer API v2 is running",
  "version": "2.0.0"
}
```

### 2. File Upload & Analysis
**POST** `/api/v2/analyze`

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `files`: List of bank statement files (CSV/Excel)
  - `from_date`: Optional start date filter (MM-YYYY)
  - `to_date`: Optional end date filter (MM-YYYY)
  - `portfolio_mode`: Optional boolean for portfolio analysis

**Response:**
```json
{
  "analysis_id": "uuid-string",
  "files_processed": 2,
  "file_names": ["statement1.csv", "statement2.xlsx"],
  "status": "completed"
}
```

### 3. Dashboard Data
**GET** `/api/v2/dashboard/{analysis_id}`

**Response:**
```json
{
  "overall_summary": {
    "total_earned": 750000.0,
    "total_spent": 680000.0,
    "net_change": 70000.0,
    "total_transactions": 1250,
    "date_range_start": "2024-01-01",
    "date_range_end": "2024-12-31"
  },
  "top_spending_categories": [
    {
      "category": "Bills & Entertainment",
      "total_debit": 45000.0,
      "debit_count": 85,
      "total_credit": 2000.0,
      "credit_count": 5,
      "net_amount": -43000.0,
      "percentage": 35.2
    }
  ],
  "top_income_categories": [
    {
      "category": "Income & Salary",
      "total_debit": 0.0,
      "debit_count": 0,
      "total_credit": 750000.0,
      "credit_count": 6,
      "net_amount": 750000.0,
      "percentage": 85.2
    }
  ],
  "recent_transactions": [
    {
      "id": "HDFC_2024-12-31_1_abc123",
      "date": "2024-12-31",
      "description": "Salary Credit",
      "amount": 75000.0,
      "category": "Income & Salary",
      "bank": "HDFC",
      "balance": 125000.0,
      "transaction_type": "credit",
      "source_file": "hdfc_statement.csv"
    }
  ]
}
```

### 4. Categories Analysis
**GET** `/api/v2/categories/{analysis_id}`

**Response:**
```json
{
  "spending_categories": [
    {
      "category": "Bills & Entertainment",
      "total_debit": 45000.0,
      "debit_count": 85,
      "total_credit": 2000.0,
      "credit_count": 5,
      "net_amount": -43000.0,
      "percentage": 35.2
    }
  ],
  "income_categories": [
    {
      "category": "Income & Salary",
      "total_debit": 0.0,
      "debit_count": 0,
      "total_credit": 750000.0,
      "credit_count": 6,
      "net_amount": 750000.0,
      "percentage": 85.2
    }
  ],
  "total_spending": 680000.0,
  "total_income": 750000.0
}
```

### 5. Transactions List
**GET** `/api/v2/transactions/{analysis_id}`

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 1000)
- `category`: Filter by category name
- `transaction_type`: Filter by "debit" or "credit"
- `search`: Search in transaction description

**Response:**
```json
{
  "transactions": [
    {
      "id": "HDFC_2024-12-31_1_abc123",
      "date": "2024-12-31",
      "description": "Salary Credit",
      "amount": 75000.0,
      "category": "Income & Salary",
      "bank": "HDFC",
      "balance": 125000.0,
      "transaction_type": "credit",
      "source_file": "hdfc_statement.csv"
    }
  ],
  "total_count": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25,
  "summary": {
    "total_earned": 750000.0,
    "total_spent": 680000.0,
    "net_change": 70000.0,
    "total_transactions": 1250,
    "date_range_start": "2024-01-01",
    "date_range_end": "2024-12-31"
  }
}
```

### 6. UPI Analysis
**GET** `/api/v2/upi-analysis/{analysis_id}`

**Response:**
```json
{
  "upi_categories": [
    {
      "category": "Food & Dining",
      "total_debit": 25000.0,
      "debit_count": 45,
      "total_credit": 1000.0,
      "credit_count": 2,
      "net_amount": -24000.0,
      "percentage": 35.7
    }
  ],
  "total_upi_debit": 70000.0,
  "total_upi_credit": 5000.0,
  "total_upi_transactions": 150,
  "net_upi_amount": -65000.0
}
```

### 7. Analysis Information
**GET** `/api/v2/analysis/{analysis_id}/info`

**Response:**
```json
{
  "analysis_id": "uuid-string",
  "total_transactions": 1250,
  "total_categories": 43,
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "last_updated": "2024-12-31 23:59:59"
}
```

### 8. List All Analyses
**GET** `/api/v2/analysis`

**Response:**
```json
{
  "analyses": [
    {
      "analysis_id": "uuid-string-1",
      "total_transactions": 1250,
      "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
      }
    }
  ]
}
```

## Data Models

### CategorySummaryV2
```json
{
  "category": "string",
  "total_debit": "number",
  "debit_count": "integer",
  "total_credit": "number",
  "credit_count": "integer",
  "net_amount": "number",
  "percentage": "number"
}
```

### TransactionV2
```json
{
  "id": "string",
  "date": "string (YYYY-MM-DD)",
  "description": "string",
  "amount": "number (positive for credit, negative for debit)",
  "category": "string",
  "bank": "string",
  "balance": "number",
  "transaction_type": "debit|credit",
  "source_file": "string"
}
```

### OverallSummaryV2
```json
{
  "total_earned": "number",
  "total_spent": "number",
  "net_change": "number",
  "total_transactions": "integer",
  "date_range_start": "string",
  "date_range_end": "string"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `HTTP_400` | Bad Request - Invalid parameters |
| `HTTP_404` | Not Found - Analysis ID not found |
| `HTTP_422` | Validation Error - Invalid data format |
| `HTTP_500` | Internal Server Error |
| `INTERNAL_ERROR` | Unexpected server error |

## Rate Limiting
Currently no rate limiting implemented (development mode).

## Frontend Integration

### React Service Example
```javascript
class FinanceAPIService {
  constructor(baseURL = 'http://localhost:8001') {
    this.baseURL = baseURL;
  }

  async uploadFiles(files, options = {}) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    if (options.fromDate) formData.append('from_date', options.fromDate);
    if (options.toDate) formData.append('to_date', options.toDate);
    
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

  async getTransactions(analysisId, options = {}) {
    const params = new URLSearchParams(options);
    const response = await fetch(`${this.baseURL}/api/v2/transactions/${analysisId}?${params}`);
    return response.json();
  }
}
```

## Testing

### Using curl
```bash
# Upload files
curl -X POST "http://localhost:8001/api/v2/analyze" \
  -F "files=@statement1.csv" \
  -F "files=@statement2.xlsx"

# Get dashboard
curl "http://localhost:8001/api/v2/dashboard/{analysis_id}"

# Get categories
curl "http://localhost:8001/api/v2/categories/{analysis_id}"

# Get transactions with pagination
curl "http://localhost:8001/api/v2/transactions/{analysis_id}?page=1&page_size=20"
```

## Changelog

### v2.0.0
- Initial v2 API release
- Proper data models with Pydantic validation
- Comprehensive endpoints for Mint-like frontend
- Pagination support for transactions
- Filtering and search capabilities
- Structured error handling
