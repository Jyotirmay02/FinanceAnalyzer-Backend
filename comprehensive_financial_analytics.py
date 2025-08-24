#!/usr/bin/env python3
"""
Comprehensive Financial Analytics for Multi-Bank Credit Card Statements
Based on the enhanced PDF parser with account summaries and transaction data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import statistics

@dataclass
class FinancialHealthMetrics:
    """Financial health scoring metrics"""
    credit_utilization_rate: float
    payment_behavior_score: float
    spending_diversity_score: float
    reward_optimization_score: float
    overall_financial_health: str
    risk_level: str

class ComprehensiveFinancialAnalyzer:
    def __init__(self, statements_dir: str = "statements"):
        self.statements_dir = statements_dir
        self.bank_data = {}
        self.load_all_statements()
    
    def load_all_statements(self):
        """Load all processed statement JSON files"""
        print("=== LOADING ALL BANK STATEMENTS ===")
        
        json_files = [f for f in os.listdir(self.statements_dir) if f.endswith('.json')]
        
        for json_file in json_files:
            if 'statement_data_' in json_file:
                # Extract bank name from filename
                parts = json_file.replace('statement_data_', '').replace('.json', '').split('_')
                bank_name = parts[0] if parts else 'Unknown'
                
                filepath = os.path.join(self.statements_dir, json_file)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if bank_name not in self.bank_data:
                            self.bank_data[bank_name] = []
                        self.bank_data[bank_name].extend(data)
                        print(f"Loaded {len(data)} statements from {bank_name}")
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
    
    def analyze_credit_utilization(self) -> Dict[str, Any]:
        """Analyze credit utilization across all banks"""
        print("\n=== CREDIT UTILIZATION ANALYSIS ===")
        
        utilization_data = {}
        total_credit_limit = 0
        total_used_credit = 0
        
        for bank, statements in self.bank_data.items():
            bank_utilization = []
            bank_credit_limit = 0
            bank_used_credit = 0
            
            for statement in statements:
                account_summary = statement.get('summary', {}).get('account_summary', {})
                
                # Handle None account_summary
                if not account_summary:
                    continue
                    
                credit_limit = account_summary.get('credit_limit')
                available_credit = account_summary.get('available_credit_limit')
                
                if credit_limit and available_credit:
                    try:
                        limit = float(str(credit_limit).replace(',', ''))
                        available = float(str(available_credit).replace(',', ''))
                        used = limit - available
                        utilization = (used / limit) * 100
                        
                        bank_utilization.append(utilization)
                        bank_credit_limit += limit
                        bank_used_credit += used
                        
                        total_credit_limit += limit
                        total_used_credit += used
                        
                        print(f"{bank}: ₹{used:,.0f} / ₹{limit:,.0f} = {utilization:.1f}%")
                    except (ValueError, TypeError) as e:
                        print(f"Error calculating utilization for {bank}: {e}")
            
            if bank_utilization:
                utilization_data[bank] = {
                    'average_utilization': statistics.mean(bank_utilization),
                    'max_utilization': max(bank_utilization),
                    'total_limit': bank_credit_limit,
                    'total_used': bank_used_credit
                }
        
        overall_utilization = (total_used_credit / total_credit_limit * 100) if total_credit_limit > 0 else 0
        
        return {
            'bank_wise': utilization_data,
            'overall_utilization': overall_utilization,
            'total_credit_limit': total_credit_limit,
            'total_used_credit': total_used_credit,
            'utilization_grade': self.grade_utilization(overall_utilization)
        }
    
    def analyze_spending_patterns(self) -> Dict[str, Any]:
        """Analyze spending patterns across all transactions"""
        print("\n=== SPENDING PATTERN ANALYSIS ===")
        
        spending_data = {
            'total_spending': 0,
            'total_payments': 0,
            'merchant_categories': {},
            'monthly_trends': {},
            'bank_wise_spending': {}
        }
        
        for bank, statements in self.bank_data.items():
            bank_spending = 0
            bank_payments = 0
            
            for statement in statements:
                transactions = statement.get('transactions', [])
                
                for txn in transactions:
                    amount = float(txn.get('amount', 0))
                    txn_type = txn.get('type', '')
                    description = txn.get('description', '')
                    merchant_category = txn.get('merchant_category', 'Other')
                    
                    if txn_type == 'debit':
                        spending_data['total_spending'] += amount
                        bank_spending += amount
                        
                        # Categorize spending
                        if merchant_category and merchant_category != 'Other':
                            category = merchant_category
                        else:
                            category = self.categorize_transaction(description)
                        
                        if category not in spending_data['merchant_categories']:
                            spending_data['merchant_categories'][category] = 0
                        spending_data['merchant_categories'][category] += amount
                        
                    elif txn_type == 'credit':
                        spending_data['total_payments'] += amount
                        bank_payments += amount
            
            spending_data['bank_wise_spending'][bank] = {
                'spending': bank_spending,
                'payments': bank_payments,
                'net': bank_spending - bank_payments
            }
            
            print(f"{bank}: Spent ₹{bank_spending:,.0f}, Paid ₹{bank_payments:,.0f}")
        
        return spending_data
    
    def analyze_reward_optimization(self) -> Dict[str, Any]:
        """Analyze reward points earning and optimization"""
        print("\n=== REWARD POINTS ANALYSIS ===")
        
        reward_data = {
            'total_points_earned': 0,
            'bank_wise_rewards': {},
            'spending_per_point': {},
            'optimization_opportunities': []
        }
        
        for bank, statements in self.bank_data.items():
            bank_points = 0
            bank_spending = 0
            
            for statement in statements:
                transactions = statement.get('transactions', [])
                
                for txn in transactions:
                    if txn.get('type') == 'debit':
                        amount = float(txn.get('amount', 0))
                        points = txn.get('reward_points', 0)
                        
                        # Handle None or invalid reward points
                        if points is None:
                            points = 0
                        else:
                            points = int(points)
                        
                        bank_spending += amount
                        bank_points += points
                        reward_data['total_points_earned'] += points
            
            if bank_points > 0:
                spending_per_point = bank_spending / bank_points
                reward_data['bank_wise_rewards'][bank] = {
                    'points_earned': bank_points,
                    'spending': bank_spending,
                    'spending_per_point': spending_per_point
                }
                reward_data['spending_per_point'][bank] = spending_per_point
                
                print(f"{bank}: {bank_points:,} points from ₹{bank_spending:,.0f} (₹{spending_per_point:.2f}/point)")
        
        return reward_data
    
    def calculate_financial_health_score(self) -> FinancialHealthMetrics:
        """Calculate comprehensive financial health score"""
        print("\n=== FINANCIAL HEALTH SCORING ===")
        
        utilization_analysis = self.analyze_credit_utilization()
        spending_analysis = self.analyze_spending_patterns()
        reward_analysis = self.analyze_reward_optimization()
        
        # Credit Utilization Score (0-100, higher is better)
        utilization_rate = utilization_analysis['overall_utilization']
        if utilization_rate <= 10:
            utilization_score = 100
        elif utilization_rate <= 30:
            utilization_score = 80
        elif utilization_rate <= 50:
            utilization_score = 60
        elif utilization_rate <= 70:
            utilization_score = 40
        else:
            utilization_score = 20
        
        # Payment Behavior Score (based on payment vs spending ratio)
        payment_ratio = spending_analysis['total_payments'] / spending_analysis['total_spending'] if spending_analysis['total_spending'] > 0 else 0
        if payment_ratio >= 0.95:
            payment_score = 100
        elif payment_ratio >= 0.80:
            payment_score = 80
        elif payment_ratio >= 0.60:
            payment_score = 60
        else:
            payment_score = 40
        
        # Spending Diversity Score
        categories = len(spending_analysis['merchant_categories'])
        diversity_score = min(100, categories * 10)  # Max 100 for 10+ categories
        
        # Reward Optimization Score
        avg_spending_per_point = statistics.mean(reward_analysis['spending_per_point'].values()) if reward_analysis['spending_per_point'] else 100
        if avg_spending_per_point <= 20:
            reward_score = 100
        elif avg_spending_per_point <= 50:
            reward_score = 80
        elif avg_spending_per_point <= 100:
            reward_score = 60
        else:
            reward_score = 40
        
        # Overall Score
        overall_score = (utilization_score + payment_score + diversity_score + reward_score) / 4
        
        # Risk Assessment
        if utilization_rate > 80:
            risk_level = "HIGH"
        elif utilization_rate > 50:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Health Grade
        if overall_score >= 90:
            health_grade = "EXCELLENT"
        elif overall_score >= 80:
            health_grade = "GOOD"
        elif overall_score >= 70:
            health_grade = "FAIR"
        else:
            health_grade = "NEEDS_IMPROVEMENT"
        
        print(f"Credit Utilization Score: {utilization_score}/100 ({utilization_rate:.1f}% utilization)")
        print(f"Payment Behavior Score: {payment_score}/100 ({payment_ratio:.1%} payment ratio)")
        print(f"Spending Diversity Score: {diversity_score}/100 ({categories} categories)")
        print(f"Reward Optimization Score: {reward_score}/100 (₹{avg_spending_per_point:.1f}/point)")
        print(f"Overall Financial Health: {health_grade} ({overall_score:.1f}/100)")
        print(f"Risk Level: {risk_level}")
        
        return FinancialHealthMetrics(
            credit_utilization_rate=utilization_rate,
            payment_behavior_score=payment_score,
            spending_diversity_score=diversity_score,
            reward_optimization_score=reward_score,
            overall_financial_health=health_grade,
            risk_level=risk_level
        )
    
    def generate_recommendations(self) -> List[str]:
        """Generate personalized financial recommendations"""
        recommendations = []
        
        utilization_analysis = self.analyze_credit_utilization()
        spending_analysis = self.analyze_spending_patterns()
        
        # Utilization recommendations
        if utilization_analysis['overall_utilization'] > 50:
            recommendations.append("🚨 HIGH PRIORITY: Reduce credit utilization below 30% to improve credit score")
        elif utilization_analysis['overall_utilization'] > 30:
            recommendations.append("⚠️ Consider reducing credit utilization below 30% for optimal credit health")
        
        # Payment recommendations
        payment_ratio = spending_analysis['total_payments'] / spending_analysis['total_spending'] if spending_analysis['total_spending'] > 0 else 0
        if payment_ratio < 0.8:
            recommendations.append("💳 Increase payment amounts to reduce outstanding balances")
        
        # Spending recommendations
        top_category = max(spending_analysis['merchant_categories'].items(), key=lambda x: x[1]) if spending_analysis['merchant_categories'] else None
        if top_category:
            recommendations.append(f"📊 Top spending category: {top_category[0]} (₹{top_category[1]:,.0f})")
        
        return recommendations
    
    def categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['amazon', 'flipkart', 'myntra', 'shopping']):
            return 'E-COMMERCE'
        elif any(word in description_lower for word in ['restaurant', 'food', 'zomato', 'swiggy']):
            return 'FOOD & DINING'
        elif any(word in description_lower for word in ['fuel', 'petrol', 'diesel', 'gas']):
            return 'FUEL'
        elif any(word in description_lower for word in ['grocery', 'supermarket', 'mart']):
            return 'GROCERY'
        elif any(word in description_lower for word in ['jio', 'airtel', 'vodafone', 'recharge']):
            return 'TELECOM'
        elif any(word in description_lower for word in ['insurance', 'policy']):
            return 'INSURANCE'
        elif any(word in description_lower for word in ['bbps', 'payment received']):
            return 'PAYMENT'
        else:
            return 'OTHER'
    
    def grade_utilization(self, utilization: float) -> str:
        """Grade credit utilization"""
        if utilization <= 10:
            return "EXCELLENT"
        elif utilization <= 30:
            return "GOOD"
        elif utilization <= 50:
            return "FAIR"
        elif utilization <= 70:
            return "POOR"
        else:
            return "CRITICAL"
    
    def export_comprehensive_report(self, filename: str = "comprehensive_financial_report.json"):
        """Export comprehensive financial analysis report"""
        report = {
            'analysis_date': datetime.now().isoformat(),
            'credit_utilization': self.analyze_credit_utilization(),
            'spending_patterns': self.analyze_spending_patterns(),
            'reward_optimization': self.analyze_reward_optimization(),
            'financial_health': self.calculate_financial_health_score().__dict__,
            'recommendations': self.generate_recommendations(),
            'summary': {
                'total_banks': len(self.bank_data),
                'total_statements': sum(len(statements) for statements in self.bank_data.values()),
                'total_transactions': sum(len(stmt.get('transactions', [])) for statements in self.bank_data.values() for stmt in statements)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n=== COMPREHENSIVE REPORT EXPORTED ===")
        print(f"Report saved to: {filename}")
        return report

def main():
    """Run comprehensive financial analysis"""
    analyzer = ComprehensiveFinancialAnalyzer()
    
    # Generate comprehensive report
    report = analyzer.export_comprehensive_report()
    
    print("\n" + "="*60)
    print("COMPREHENSIVE FINANCIAL ANALYSIS COMPLETE")
    print("="*60)
    
    # Display key insights
    print(f"📊 Analyzed {report['summary']['total_statements']} statements from {report['summary']['total_banks']} banks")
    print(f"💳 Total transactions processed: {report['summary']['total_transactions']:,}")
    print(f"🎯 Overall credit utilization: {report['credit_utilization']['overall_utilization']:.1f}%")
    print(f"💰 Total spending: ₹{report['spending_patterns']['total_spending']:,.0f}")
    print(f"🏆 Financial health grade: {report['financial_health']['overall_financial_health']}")
    
    print("\n📋 TOP RECOMMENDATIONS:")
    for i, rec in enumerate(report['recommendations'][:3], 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    main()
