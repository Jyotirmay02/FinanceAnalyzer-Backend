#!/usr/bin/env python3
"""
Start the FinanceAnalyzer Backend Server
"""

import uvicorn
import sys
from pathlib import Path

def main():
    """Main function to start the server"""
    print("🚀 Starting FinanceAnalyzer Backend Server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📖 API docs available at: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "api_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
