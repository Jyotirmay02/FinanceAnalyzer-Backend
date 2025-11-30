# Database Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies
```bash
pip install sqlalchemy alembic
```

### 2. Initialize Database
```bash
python -c "from src.database import init_db; init_db()"
```

### 3. Verify Setup
```bash
python test_database.py
```

**Done!** Database created at: `~/Documents/FinanceAnalyzer/finance_data.db`

---

## 📊 Common Operations

### Add Transaction
```python
from src.database import SessionLocal, DatabaseService
from datetime import date

db = SessionLocal()
service = DatabaseService(db)

txn = service.add_transaction({
    'date': date(2025, 1, 15),
    'amount': 500.0,
    'description': 'AMAZON Purchase',
    'type': 'debit',
    'bank': 'ICICI_CC',
    'category': 'Shopping',
    'merchant': 'AMAZON'
})

db.close()
```

### Query Transactions
```python
# Get all transactions
transactions = service.get_transactions(limit=100)

# Filter by date
from datetime import datetime
transactions = service.get_transactions(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 12, 31)
)

# Filter by category
transactions = service.get_transactions(category_id=1)
```

### Get Summary
```python
stats = service.get_summary_stats()
print(f"Total Spent: ₹{stats['total_spent']}")
print(f"Total Earned: ₹{stats['total_earned']}")
print(f"Net Change: ₹{stats['net_change']}")
```

---

## 🔧 Schema Changes

### Add New Column
```bash
# 1. Edit src/database/models.py
# Add: notes = Column(Text)

# 2. Generate migration
alembic revision --autogenerate -m "add notes column"

# 3. Apply migration
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

---

## 💾 Backup

### Manual Backup
```bash
cp ~/Documents/FinanceAnalyzer/finance_data.db ~/Backups/
```

### Automated Backup Script
```python
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "Documents/FinanceAnalyzer/finance_data.db"
BACKUP_DIR = Path.home() / "Backups/FinanceAnalyzer"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

backup_file = BACKUP_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy2(DB_PATH, backup_file)
print(f"Backup created: {backup_file}")
```

---

## 🐛 Troubleshooting

### Database Locked Error
```python
# Use context manager to ensure connections close
from src.database import SessionLocal

with SessionLocal() as db:
    service = DatabaseService(db)
    # Do operations
    # Connection auto-closes
```

### Reset Database
```bash
# Delete database file
rm ~/Documents/FinanceAnalyzer/finance_data.db

# Recreate
python -c "from src.database import init_db; init_db()"
```

### Check Database Size
```python
from src.database import get_db_info
print(get_db_info())
```

---

## 📚 Full Documentation

For comprehensive documentation including:
- Architecture decisions
- Schema design rationale
- Performance characteristics
- Migration strategies

See: **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)**
