# Mobile App Testing Guide

## Current Status

**Backend:** ✅ Ready with new preview/save endpoints  
**Mobile App:** ⚠️ Needs update to use new endpoints

---

## Quick Test (Without Mobile App Changes)

### Option 1: Test with curl (Simulates Mobile App)

```bash
# 1. Start backend server
cd /Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend
python api_v2_server.py

# 2. Test portfolio endpoint (simulates mobile app query)
curl http://localhost:8001/api/v2/portfolio/summary

# Response shows current data in database
```

### Option 2: Test with Postman/Thunder Client

1. **GET** `http://localhost:8001/api/v2/portfolio/summary`
2. See current portfolio data
3. **GET** `http://localhost:8001/api/v2/portfolio/transactions?limit=10`
4. See individual transactions

---

## Testing from Mobile App (Current Setup)

### Current Mobile App Flow

The mobile app currently uses:
- `POST /api/v2/upload` - Direct upload (old flow)
- `GET /api/v2/dashboard/{analysis_id}` - Get dashboard

**This still works!** But data goes to in-memory storage, not database.

### To Test Current Mobile App

1. **Start backend:**
   ```bash
   cd /Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend
   python api_v2_server.py
   ```

2. **Update mobile app backend URL:**
   
   File: `src/services/BackendService.ts`
   ```typescript
   // For Android emulator
   const BASE_URL = 'http://10.0.2.2:8001';
   
   // For physical device (use your computer's IP)
   const BASE_URL = 'http://192.168.1.X:8001';  // Replace X with your IP
   ```

3. **Find your computer's IP:**
   ```bash
   # macOS
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Should show something like: inet 192.168.1.105
   ```

4. **Run mobile app:**
   ```bash
   cd /Users/jmysethi/Documents/Finance/FinanceAnalyzer-Mobile
   npx expo run:android
   ```

5. **Test upload:**
   - Open app → Upload tab
   - Select Excel/PDF file
   - Upload should work with old flow

---

## Updating Mobile App for New Flow (Required)

To use the new preview/save flow, update the mobile app:

### Step 1: Add New API Methods

File: `src/services/BackendService.ts`

```typescript
// Add these methods to BackendService class

static async uploadPreview(file: File): Promise<{
  upload_id: string;
  transaction_count: number;
  summary: any;
}> {
  const formData = new FormData();
  formData.append('files', file);
  
  const response = await fetch(`${BASE_URL}/api/v2/upload/preview`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }
  
  return response.json();
}

static async saveUpload(uploadId: string): Promise<{
  saved: number;
  duplicates: number;
  message: string;
}> {
  const response = await fetch(
    `${BASE_URL}/api/v2/upload/${uploadId}/save`,
    { method: 'POST' }
  );
  
  if (!response.ok) {
    throw new Error(`Save failed: ${response.statusText}`);
  }
  
  return response.json();
}

static async getPortfolioSummary(): Promise<any> {
  const response = await fetch(`${BASE_URL}/api/v2/portfolio/summary`);
  
  if (!response.ok) {
    throw new Error(`Portfolio fetch failed: ${response.statusText}`);
  }
  
  return response.json();
}
```

### Step 2: Update Upload Screen

File: `src/screens/UploadScreen.tsx`

Add preview state and save button:

```typescript
const [previewData, setPreviewData] = useState<any>(null);
const [uploadId, setUploadId] = useState<string | null>(null);

const handleUploadPreview = async (file: File) => {
  try {
    const result = await BackendService.uploadPreview(file);
    setUploadId(result.upload_id);
    setPreviewData(result);
    
    // Show preview dialog
    Alert.alert(
      'Preview Upload',
      `Transactions: ${result.transaction_count}\n` +
      `Total Spent: ₹${result.summary.total_spent}\n` +
      `Total Earned: ₹${result.summary.total_earned}\n\n` +
      `Save to your portfolio?`,
      [
        { text: 'Discard', style: 'cancel' },
        { text: 'Save', onPress: () => handleSave(result.upload_id) }
      ]
    );
  } catch (error) {
    Alert.alert('Error', error.message);
  }
};

const handleSave = async (uploadId: string) => {
  try {
    const result = await BackendService.saveUpload(uploadId);
    Alert.alert(
      'Success',
      `${result.message}\n\n` +
      `New: ${result.saved}\n` +
      `Duplicates: ${result.duplicates}`
    );
    setPreviewData(null);
    setUploadId(null);
  } catch (error) {
    Alert.alert('Error', error.message);
  }
};
```

### Step 3: Update Dashboard

File: `src/screens/DashboardScreen.tsx`

Use portfolio endpoint instead of analysis_id:

```typescript
const fetchDashboard = async () => {
  try {
    const data = await BackendService.getPortfolioSummary();
    // Update state with data.summary and data.categories
  } catch (error) {
    console.error('Dashboard fetch failed:', error);
  }
};
```

---

## Quick Test Without Mobile App Changes

### Test the new endpoints directly:

```bash
# 1. Check current portfolio
curl http://localhost:8001/api/v2/portfolio/summary

# 2. Add test transaction via Python
cd /Users/jmysethi/Documents/Finance/FinanceAnalyzer-Backend
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.append(str(Path.cwd() / "src"))

from database import SessionLocal, DatabaseService
from datetime import date

db = SessionLocal()
service = DatabaseService(db)

txn = service.add_transaction({
    'date': date(2025, 1, 20),
    'amount': 750.0,
    'description': 'NETFLIX Subscription',
    'type': 'debit',
    'bank': 'HDFC_CC',
    'category': 'Entertainment',
    'merchant': 'NETFLIX',
    'year': 2025
})

print(f"✓ Added: NETFLIX - ₹750")
db.close()
EOF

# 3. Check updated portfolio
curl http://localhost:8001/api/v2/portfolio/summary
```

---

## Summary

### ✅ What Works Now
- Backend API with database storage
- Portfolio summary endpoint
- Transaction query endpoint
- Preview/save flow endpoints

### ⚠️ What Needs Update
- Mobile app to use new endpoints
- Preview screen in mobile app
- Save/Discard buttons

### 🚀 Fastest Way to Test

**Option 1:** Use curl commands above (no mobile app needed)

**Option 2:** Update 3 files in mobile app:
1. `BackendService.ts` - Add new methods (5 min)
2. `UploadScreen.tsx` - Add preview/save flow (10 min)
3. `DashboardScreen.tsx` - Use portfolio endpoint (5 min)

**Total time:** ~20 minutes to update mobile app

---

## Next Steps

1. **Test backend directly** (curl commands above) ✅ Works now
2. **Update mobile app** (optional, for full flow)
3. **Test with real bank statements**

The backend is fully functional and tested. Mobile app updates are optional but recommended for the preview/save flow!
