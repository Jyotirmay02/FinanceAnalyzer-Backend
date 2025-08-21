# FinanceAnalyzer Complete Setup Guide

Complete setup instructions for running the FinanceAnalyzer application with both backend and frontend servers.

## 🎯 Overview

The FinanceAnalyzer consists of two main components:
- **Backend**: Python FastAPI server (Port 8000)
- **Frontend**: React web application (Port 3000)

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** (for backend)
- **Poetry** (recommended for Python dependency management)
- **Node.js 16+** and **npm** (for frontend)
- **Git** (for cloning repositories)
- **Terminal/Command Prompt** access

### Verify Prerequisites
```bash
# Check Python version
python --version  # Should be 3.8+

# Check Poetry installation
poetry --version  # Should show Poetry version

# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Check Node.js version
node --version    # Should be 16+

# Check npm version
npm --version

# Check Git
git --version
```

## 🚀 Complete Setup (First Time)

### Step 1: Clone Repositories
```bash
# Create a workspace directory
mkdir FinanceAnalyzer-Workspace
cd FinanceAnalyzer-Workspace

# Clone backend repository
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Backend.git

# Clone frontend repository
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Frontend.git

# Your directory structure should look like:
# FinanceAnalyzer-Workspace/
# ├── FinanceAnalyzer-Backend/
# └── FinanceAnalyzer-Frontend/
```

### Step 2: Setup Backend
```bash
# Navigate to backend directory
cd FinanceAnalyzer-Backend

# Install Python dependencies using Poetry (recommended)
poetry install

# Alternative: Using pip
pip install -r requirements.txt

# Verify installation using Poetry
poetry run python -c "import fastapi, pandas, numpy; print('✅ Backend dependencies installed')"

# Or without Poetry
python -c "import fastapi, pandas, numpy; print('✅ Backend dependencies installed')"
```

### Step 3: Setup Frontend
```bash
# Navigate to frontend directory (from workspace root)
cd ../FinanceAnalyzer-Frontend

# Install Node.js dependencies
npm install

# Verify installation
npm list react react-dom @mui/material
```

## 🖥️ Running the Application

### Method 1: Two Terminal Setup (Recommended)

**Terminal 1 - Backend Server:**
```bash
cd FinanceAnalyzer-Backend
poetry run python start_server.py

# Or without Poetry:
# python start_server.py

# Expected output:
# INFO:     Started server process
# INFO:     Uvicorn running on http://0.0.0.0:8000
# ✅ Backend running on http://localhost:8000
```

**Terminal 2 - Frontend Server:**
```bash
cd FinanceAnalyzer-Frontend
npm start

# Expected output:
# Compiled successfully!
# Local:            http://localhost:3000
# ✅ Frontend running on http://localhost:3000
```

### Method 2: Background Process Setup
```bash
# Start backend in background using Poetry
cd FinanceAnalyzer-Backend
poetry run python start_server.py &
BACKEND_PID=$!

# Start frontend in background
cd ../FinanceAnalyzer-Frontend
npm start &
FRONTEND_PID=$!

# To stop later:
# kill $BACKEND_PID $FRONTEND_PID
```

## ✅ Verification Steps

### 1. Backend Verification
```bash
# Test health endpoint
curl http://localhost:8000/

# Expected response:
# {"message":"FinanceAnalyzer API is running","version":"1.0.0"}

# Check API documentation
# Open: http://localhost:8000/docs
```

### 2. Frontend Verification
```bash
# Open browser and navigate to:
# http://localhost:3000

# You should see:
# - FinanceAnalyzer navigation bar
# - Dashboard page with "No data available" message
# - Upload link in navigation
```

### 3. End-to-End Test
```bash
# 1. Go to http://localhost:3000/upload
# 2. Upload a sample file (if available)
# 3. Verify redirect to dashboard
# 4. Check that data appears in dashboard
```

## 📁 Sample Data (Optional)

If you have sample data files, place them in a `data/` directory:
```bash
# Create data directory in backend
cd FinanceAnalyzer-Backend
mkdir -p data

# Add your bank statement files:
# data/
# ├── SBI_2024.xls
# ├── statement.csv
# └── other_files.xlsx
```

## 🔧 Development Workflow

### Daily Development
```bash
# Start both servers (two terminals)
# Terminal 1:
cd FinanceAnalyzer-Backend && poetry run python start_server.py

# Terminal 2:
cd FinanceAnalyzer-Frontend && npm start

# Both servers will auto-reload on file changes
```

### Making Changes
```bash
# Backend changes:
# - Edit files in src/ directory
# - Server auto-reloads (if using --reload flag)

# Frontend changes:
# - Edit files in src/ directory
# - Browser auto-refreshes
```

## 🚨 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process using port 8000
kill -9 $(lsof -t -i:8000)

# Check what's using port 3000
lsof -i :3000
kill -9 $(lsof -t -i:3000)
```

**Backend Won't Start:**
```bash
# Check Python version
python --version

# Reinstall dependencies using Poetry
poetry install

# Or using pip
pip install -r requirements.txt

# Check for import errors using Poetry
poetry run python -c "from src.finance_analyzer import FinanceAnalyzer"

# Or without Poetry
python -c "from src.finance_analyzer import FinanceAnalyzer"
```

**Frontend Won't Start:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node.js version
node --version  # Should be 16+
```

**CORS Errors:**
```bash
# Verify backend CORS settings in api_server.py
# Should include: "http://localhost:3000"

# Check browser console for specific CORS errors
# Open Developer Tools → Console
```

**File Upload Issues:**
```bash
# Check file format (CSV, XLS, XLSX only)
# Check file size (should be reasonable)
# Verify backend logs for detailed errors
```

### Debug Mode

**Backend Debug:**
```bash
# Run with verbose logging using Poetry
poetry run python start_server.py --log-level debug

# Or without Poetry
python start_server.py --log-level debug
```

**Frontend Debug:**
```bash
# Enable debug mode
REACT_APP_DEBUG=true npm start

# Check browser console for detailed logs
```

## 📊 Usage Examples

### Basic Usage Flow
1. **Start Servers**: Backend (8000) + Frontend (3000)
2. **Upload File**: Go to `/upload`, select bank statement
3. **View Results**: Dashboard shows analysis automatically
4. **Explore Data**: Use navigation to view Categories, UPI Analysis, Transactions

### API Testing
```bash
# Test file upload via API
curl -X POST "http://localhost:8000/api/analyze" \
  -F "files=@path/to/your/statement.xls"

# Response will include analysis_id for further queries
```

## 🔄 Updates & Maintenance

### Updating Code
```bash
# Update backend
cd FinanceAnalyzer-Backend
git pull origin main
poetry install  # If dependencies changed

# Or without Poetry:
# pip install -r requirements.txt

# Update frontend
cd ../FinanceAnalyzer-Frontend
git pull origin main
npm install  # If dependencies changed
```

### Backup & Restore
```bash
# Backup generated reports
cp -r FinanceAnalyzer-Backend/visuals/ backup/

# Backup configuration
cp FinanceAnalyzer-Backend/requirements.txt backup/
cp FinanceAnalyzer-Frontend/package.json backup/
```

## 📞 Support

### Getting Help
1. **Check Logs**: Look at terminal output for error messages
2. **Browser Console**: Check for frontend JavaScript errors
3. **API Documentation**: Visit http://localhost:8000/docs
4. **GitHub Issues**: Create issues in respective repositories

### Useful Commands
```bash
# Check running processes
ps aux | grep python  # Backend processes
ps aux | grep node    # Frontend processes

# Check port usage
netstat -tulpn | grep :8000  # Backend port
netstat -tulpn | grep :3000  # Frontend port

# System resource usage
top -p $(pgrep -f "python.*start_server")
top -p $(pgrep -f "node.*react-scripts")
```

---

## 🎉 Quick Start Summary

```bash
# 1. Clone repositories
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Backend.git
git clone https://github.com/Jyotirmay02/FinanceAnalyzer-Frontend.git

# 2. Install dependencies
cd FinanceAnalyzer-Backend && poetry install
cd ../FinanceAnalyzer-Frontend && npm install

# 3. Start servers (two terminals)
# Terminal 1: cd FinanceAnalyzer-Backend && poetry run python start_server.py
# Terminal 2: cd FinanceAnalyzer-Frontend && npm start

# 4. Open browser: http://localhost:3000
# 5. Upload file and analyze!
```

**That's it! You now have a fully functional FinanceAnalyzer setup.** 🚀
