"""
UPI Transaction Subcategorization with Hierarchical Structure
"""

import re
from typing import Dict, List

# Hierarchical UPI categorization structure
UPI_CATEGORIES = {
    "Construction": {
        "Plot Purchase": ["sujitsaho"],
        "Plot Purchase - TDS": ["Central B"],
        "Home Loan": ["LIC HOUSI"],
        "Contractor": ["Bijay  Je", "KAHNU CH"],
        "Architect": ["Vedanti S"],
        "Cement": ["Bijan Kum", "MANORANJA", "Manoj K T", "Rabindra"],
        "Brick": ["Shyamsundar", "Shyamsund", "Mita Brick", "MITA BRIC", "HARISCHAN", "DILLIP KU"],
        "Sand": ["Manoranjana", "Mr SRIKANTH", "Mr SRIKAN"],
        "Chips": ["NARENDRA /INDB/**76191"],
        "Wood": ["Gobinda S", "RABI NARAY", "BALAI CHA", "wood"],
        "Gangadhar Hardware": ["Pratik Ku", "47250211696"],
        "Grill": ["SWARUP KU"],
        "Electrician": ["MAHENDRA", "Electician"],
        "Electric Appliance": ["GOPAL SAHU"],
        "Plumbing": ["Mamashre", "MS PALLA"],
        "Plumber": ["TAPAN KU"],
        "Construction UNKNOWN": ["ABINASH"]
    },
    "Investment": {
        "NPS": ["NPS TRUST"],
        "Mutual Fund": ["IndianCle", "mutual", "indianclearingcorp"],
        "Trading": ["zerodha", "groww"],
        "Aadhaar": ["UNIQUE ID"],
    },
    "Rent & Housing": {
        "Rent": ["Prasad", "Bhavanipr", "Sheeba Ga", "NAGIREDDY"],
        "Flat Advance": ["Lokendra"],
        "Flat Expense": ["Ankit Kho"]
    },
    "Credit Card Payment": {
        "CRED": ["CRED/", "CRED FLASH", "CredClub", "CREDPAYCR", "CRED Club", "Axis/UTIB/**.club"],
        "Cheq": ["Cheq Digi", "Cheq"]
    },
    "Bills & Entertainment": {
        "Internet Bill": ["Act  Broa"],
        "Entertainment": ["Torq 03 S"],
        "Donation": ["Iskcon", "BAL RAKSH", "SRIJAGANNAT"],
        "Temple Offering": ["N RAVIKU/FDRL", "BASKAR S/CNRB"],
        "Snacks": ["TULASI JU", "Kanti Sw", "GOVINDAS", "TULASI J"],
        "Food & Dining": ["CREDPAYSW", "CREDPAYDU", "/Axis/UTIB/**wiggy", "RAHUL TOS", "AASHUTOSH", "ASHUTOSH", "SENDHOOR", "Madurai I", "EatClub", 
                          "UDUPI  AA", "TSF FOOD", "FOOD", "Sri Udupi", "Compass", "SOUTHERN", "SENDOOR C", "AU FACILI", "AU HOSPIT", "swiggy", 
                          "zomato", "dominos", "mcdonald", "SmartQ"],
        "Utilities": ["CREDPAYEA", "CRED TELE", "EURONETGP", "Bhavani T", "HAPPY HOM", "RAJURAM", "RAJU RAM", "TP NORTHE"],
        "Mobile Recharge": ["airtel", "jio", "vi ", "recharge"],
        "Fitness": ["1RM FITNE"],
        "Health-Med": ["SLV MEDIC", "MANOJ MED", "DR PRAVEE"],
        "Salon": ["SURESHA N"],
        "Drinking Water": ["S NAGARAJ"],
    },
    "Shopping": {
        "E-commerce": ["amazon", "flipkart", "myntra", "Ratnadeep", "Axis/UTIB/**onupi", "rituraj", "nothi"],
        "Quick Commerce": ["Dunzo", "Swiggy Instamart", "Zepto", "Blinkit", "Geddit", "bigbasket", "grofers"],
        "Clothing": ["clothing", "DAGA DRES", "MEESHO", "FASHION F", "Kalinga F", "FIRE BIRD", "SHREE ASH", "Ags retai", "HERITAGE /YESB/**88594"],
        "Delivery": ["EKART", "ECOMEXPRE"],
        "Apparels": ["BATA INDI"],
    },
    "Travel": {
        "Train Booking": ["irctc", "ixigo"],
        "Cab Service": ["ola", "uber"],
        "Bus Booking": ["redbus"],
        "AirTravel": ["goibibo", "MOBIKWIK", "AKASA AIR", "SANDEEP K/HDFC/**pk318", "Fligh"],
        "Transport": ["BASAVARAJ", "RAMASINGH"],
        "Daily Commute": ["Roppen Tr", "BMTC", "Rapido", "Bangalore/INDB", "BANGALOR/UTIB", "BANGALOR/INDB"],
        "Daily Commute (rapido/uber)": ["ASMA BANU", "Mr VINOD", "G MAHESH", "LOKESH/KKBK", "RIYAZ AH", "MUNIKRIS"],
    },
    "Lending": {
        "Lipu": ["PRAHLLAD", "Mr PRAHLLAD", "Mr PRAHLL"]
    },
    "Wallet": {
        "Paytm": ["Add Money/PYTM"],
        "Amazon": ["amzn1.acc/UTIB/**eload@apl"],
        "Gpay": ["Gpay", "Google In"],
    },
    "Cashbacks": {
        "Cashback": ["CASHBACK", "CASHBACKS", "CASHBACK OFFER", "GOOGLEPAY"],
    },
    "Friends": {
        "Arunanshu": ["ARUNANSHU"],
        "Ashwani": ["ashwanijh"],
        "Atul": ["ATUL KAIL"],
        "Bhajan": ["BHAJAN KU", "KUVERA EN", "BHAJAN"],
        "Bishnu": ["BISHNU PR"],
        "Biswajit": ["BISWAJIT /PUNB"],
        "Debabrat": ["MOTO WORLD", "DEBABRAT"],
        "Dhruv": ["DHRUV R"],
        "Kalandi": ["Kalandi"],
        "Lalit": ["LALIT   K"],
        "Madhur": ["MADHUR  M", "Mr Madhur"],
        "Maheswar": ["MAHESWAR"],
        "Manjeet": ["Manjeet"],
        "Pallove": ["PALLOVE"],
        "Pintu": ["Pintu"],
        "Rajesh": ["RAJESH"],
        "Rajkishore": ["RAJKISHOR"],
        "Ritesh": ["RITESH  C"],
        "Ronak": ["RONAK JUG"],
        "Rudra Narayan": ["RUDRA NAR", "RUDRA NA", "rudranaray"],
        "Sashikanta": ["SASHIKANT"],
        "Saswat": ["SASWAT KU"],
        "Satyajit": ["SATYAJIT"],
        "Satyapriya": ["SATYAPRIY"],
        "Sonal": ["SONALI"],
        "Soubhagya": ["Soubhagya"],
        "Suraj": ["SURAJ SU", "Suraj  Su"],
        "Suresh": ["SURESH KU"],
        "Parshu": ["SRIKANTA"],
        "Md Altaf": ["Md Altaf"],
        "Surya Kant": ["SURYA KANT"],
        "Sumit": ["SUMIT KUM"],
        "Ayush Amazon": ["AYUSH  RAJ"],
        "Sudipta Biswas": ["SUDIPTA"],
        "Ayushi Rastogi": ["AYUSHI RA"],
        "Prayag Shooken": ["PRAYAG SH"],
        "Mommy - (Piku apa)": ["BHARAT CH"],
        "Self Transfer": ["Jyotirmay", "JYOTIRMA"],
        "Abinash": ["Abinas  S/SBIN/**014-1", "Abinas"],
    },
    "Misc-Tech": {
        "Uni Pay": ["NORTHERN", "Uni Cards"],
        "Salary": ["112662223"],
    }
}

def _build_flat_keywords() -> Dict[str, str]:
    """Build flat keyword dictionary from hierarchical structure"""
    keywords = {}
    
    for level1, subcategories in UPI_CATEGORIES.items():
        for level2, keyword_list in subcategories.items():
            for keyword in keyword_list:
                keywords[keyword] = f"UPI-{level1}-{level2}"
    
    return keywords

# Build the flat keywords dictionary for backward compatibility
UPI_CONSTRUCTION_KEYWORDS = _build_flat_keywords()

def get_upi_subcategory(description: str) -> str:
    """
    Categorize UPI transaction into construction-related subcategories
    
    Args:
        description: UPI transaction description
        
    Returns:
        UPI subcategory or "UPI-Others" if no match
    """
    if not description:
        return "UPI-Others"
    
    desc_lower = description.lower()
    
    # Sort by length (longest first) for better matching
    sorted_keywords = sorted(UPI_CONSTRUCTION_KEYWORDS.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword.lower() in desc_lower:
            return UPI_CONSTRUCTION_KEYWORDS[keyword]
    
    return "UPI-Others"

def analyze_construction_spending(df) -> Dict[str, float]:
    """
    Analyze construction spending from UPI transactions
    
    Args:
        df: DataFrame with transactions
        
    Returns:
        Dictionary with construction spending breakdown
    """
    upi_transactions = df[df['Category'] == 'UPI Transfer'].copy()
    
    # Apply subcategorization
    upi_transactions['UPI_Subcategory'] = upi_transactions['Description'].apply(get_upi_subcategory)
    
    # Calculate spending by subcategory
    construction_spending = {}
    construction_categories = [cat for cat in UPI_CONSTRUCTION_KEYWORDS.values() if cat.startswith('UPI-') and cat != 'UPI-Others']
    
    for category in set(construction_categories):
        amount = upi_transactions[upi_transactions['UPI_Subcategory'] == category]['Debit (₹)'].sum()
        if amount > 0:
            construction_spending[category] = amount
    
    # Add total construction spending
    total_construction = sum(construction_spending.values())
    construction_spending['Total Construction'] = total_construction
    
    return construction_spending
