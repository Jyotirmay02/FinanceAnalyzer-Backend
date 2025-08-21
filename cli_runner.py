#!/usr/bin/env python3
"""
CLI Runner for FinanceAnalyzer
Simple wrapper to test CLI functionality
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from finance_analyzer import FinanceAnalyzer
from excel_writer import ExcelWriter

def test_cli_functionality():
    """Test CLI functionality with sample data"""
    print("🧪 Testing CLI Functionality")
    print("=" * 50)
    
    # Test with SBI_2024.xls
    input_file = Path("../FinanceAnalyzer/data/SBI_2024.xls")
    output_file = Path("cli_test_output.xlsx")
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return False
    
    try:
        print(f"📂 Input: {input_file}")
        print(f"📄 Output: {output_file}")
        
        # Initialize analyzer with input file
        analyzer = FinanceAnalyzer(str(input_file))
        
        # Run full analysis (this does everything)
        print("🔄 Running full analysis...")
        output_path = analyzer.run_full_analysis()
        
        print(f"✅ CLI test successful!")
        print(f"📊 Generated: {output_path}")
        
        # Check if Excel file was created
        if Path(output_path).exists():
            print(f"📄 Excel file size: {Path(output_path).stat().st_size:,} bytes")
        
        # Also test manual Excel generation
        print("🔄 Generating additional Excel report...")
        writer = ExcelWriter(str(output_file))
        writer.write_analysis_report(
            analyzer.categorized_df,
            analyzer.overall_summary, 
            analyzer.category_summary
        )
        
        if output_file.exists():
            print(f"📄 Additional report: {output_file} ({output_file.stat().st_size:,} bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cli_functionality()
    sys.exit(0 if success else 1)
