#!/usr/bin/env python3
"""
Enhanced ICICI Parser - Specifically designed to handle ICICI statement format
Based on the observed pattern from the debug output
"""

import re
import os
from pdf_statement_parser import ImprovedPDFParser, AccountSummary

class ICICIEnhancedParser(ImprovedPDFParser):
    def extract_account_summary_icici_enhanced(self, text: str) -> AccountSummary:
        """Enhanced ICICI account summary extraction based on observed format"""
        summary = AccountSummary()
        lines = text.split('\n')
        
        print("=== ENHANCED ICICI ACCOUNT SUMMARY EXTRACTION ===")
        
        for i, line in enumerate(lines):
            # Look for STATEMENT SUMMARY section
            if 'STATEMENT SUMMARY' in line:
                print(f"Found STATEMENT SUMMARY at line {i}")
                
                # Process next 10 lines for account summary data
                for j in range(i+1, min(i+11, len(lines))):
                    current_line = lines[j].strip()
                    print(f"Line {j}: {current_line}")
                    
                    # Total Amount due pattern: `36,472.43 = + + -
                    if 'Total Amount due' in current_line:
                        # Look for amount in next line
                        if j+1 < len(lines):
                            amount_line = lines[j+1].strip()
                            amount_match = re.search(r'`([\d,]+\.?\d*)', amount_line)
                            if amount_match:
                                summary.total_amount_due = float(amount_match.group(1).replace(',', ''))
                                print(f"  ✓ Total Amount Due: ₹{summary.total_amount_due}")
                    
                    # Minimum Amount due pattern
                    elif 'Minimum Amount due' in current_line:
                        # Look for amount in next line
                        if j+1 < len(lines):
                            amount_line = lines[j+1].strip()
                            amount_match = re.search(r'`([\d,]+\.?\d*)', amount_line)
                            if amount_match:
                                summary.minimum_amount_due = amount_match.group(1)
                                print(f"  ✓ Minimum Amount Due: ₹{summary.minimum_amount_due}")
                    
                    # Credit limits pattern: `1,00,000.00 `62,804.37 `10,000.00 `0.00
                    elif 'Credit Limit' in current_line and 'Available Credit' in current_line:
                        # Look for amounts in next few lines
                        for k in range(j+1, min(j+4, len(lines))):
                            amounts_line = lines[k].strip()
                            amounts = re.findall(r'`([\d,]+\.?\d*)', amounts_line)
                            if len(amounts) >= 4:
                                summary.credit_limit = amounts[0]
                                summary.available_credit_limit = amounts[1]
                                summary.cash_limit = amounts[2]
                                summary.available_cash_limit = amounts[3]
                                print(f"  ✓ Credit Limit: ₹{summary.credit_limit}")
                                print(f"  ✓ Available Credit: ₹{summary.available_credit_limit}")
                                print(f"  ✓ Cash Limit: ₹{summary.cash_limit}")
                                print(f"  ✓ Available Cash: ₹{summary.available_cash_limit}")
                                break
                
                # Stop after processing STATEMENT SUMMARY section
                break
        
        return summary
    
    def process_icici_with_enhanced_summary(self):
        """Process ICICI statements with enhanced account summary extraction"""
        icici_dir = "statements"
        
        # Find ICICI JSON files
        json_files = [f for f in os.listdir(icici_dir) if 'ICICI' in f and f.endswith('.json')]
        
        if not json_files:
            print("No ICICI JSON files found")
            return
        
        print(f"Found {len(json_files)} ICICI files")
        
        # Also process original PDFs if available
        pdf_dirs = [
            "statements/ICICI", 
            "../Financial Records/Credit Card/ICICI/Amazon Pay",
            "Financial Records/Credit Card/ICICI/Amazon Pay"
        ]
        
        for pdf_dir in pdf_dirs:
            if os.path.exists(pdf_dir):
                pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
                print(f"Found {len(pdf_files)} ICICI PDF files in {pdf_dir}")
                
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(pdf_dir, pdf_file)
                    try:
                        print(f"\n=== PROCESSING {pdf_file} ===")
                        text = self.extract_text_from_pdf(pdf_path)
                        enhanced_summary = self.extract_account_summary_icici_enhanced(text)
                        
                        # Display results
                        print(f"\n=== ENHANCED SUMMARY RESULTS ===")
                        if enhanced_summary.credit_limit:
                            credit_limit = float(enhanced_summary.credit_limit.replace(',', ''))
                            available_credit = float(enhanced_summary.available_credit_limit.replace(',', ''))
                            used_credit = credit_limit - available_credit
                            utilization = (used_credit / credit_limit) * 100
                            
                            print(f"Credit Limit: ₹{credit_limit:,.0f}")
                            print(f"Available Credit: ₹{available_credit:,.0f}")
                            print(f"Used Credit: ₹{used_credit:,.0f}")
                            print(f"Utilization Rate: {utilization:.1f}%")
                            
                            if enhanced_summary.minimum_amount_due:
                                print(f"Minimum Amount Due: ₹{enhanced_summary.minimum_amount_due}")
                            if enhanced_summary.total_amount_due:
                                print(f"Total Amount Due: ₹{enhanced_summary.total_amount_due:,.0f}")
                        
                    except Exception as e:
                        print(f"Error processing {pdf_file}: {e}")

def main():
    """Test enhanced ICICI parser"""
    parser = ICICIEnhancedParser()
    parser.process_icici_with_enhanced_summary()

if __name__ == "__main__":
    main()
