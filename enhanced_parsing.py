import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import time
from difflib import SequenceMatcher
from datetime import datetime



class EnhancedMessageParser:
    def __init__(self):
        # --- Robust OTP Extraction Patterns ---
        self.otp_patterns = [
            r'(?:otp|code|password)\s*is\s*[:\s]*(\d{3}[- ]?\d{3})\b',
            r'\b(\d{3}[- ]?\d{3})\s*is\s*your\s*(?:instagram|signal|discord)?\s*(?:login|verification|registration)?\s*code',
            r'(?:otp|code|password|is|:)\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code)',
            r'enter\s*(\d{4,8})\s*to',
            r'\b[gG]-(\d{6})\b'
        ]

        # --- EMI Amount Extraction Patterns ---
        self.emi_amount_patterns = [
            r'emi\s*(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'emi\s*(?:amount\s*)?(?:is\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:loan\s*)?emi\s*(?:amount\s*)?(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)[/-]*\s*(?:for|is)\s*(?:your\s*)?(?:loan\s*)?emi',
            r'emi\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)[,\s]*(?:emi|loan)',
            r'outstanding.*?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'overdue.*?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)'
        ]

        # --- EMI Due Date Patterns ---
        self.emi_due_date_patterns = [
            r'due\s*(?:on\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:pay\s*)?(?:by\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'for\s*([a-z]{3}\'?\d{4})',  # Jul'2024
            r'for\s*(?:the\s*month\s*of\s*)?([a-z]{3,9}\s*\d{4})',  # July 2024
            r'last\s*emi\s*payment.*?for[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'ending\s*on[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]

        # --- ENHANCED: Traffic Challan Patterns with NEW missing patterns ---
        self.challan_number_patterns = [
            # Traditional challan numbers
            r'challan\s*(?:bearing\s*)?(?:no\.?\s*)?([A-Z]{2}\d{17,20})',  # DL116709240411110024
            r'challan\s*(?:no\.?\s*)?([A-Z]{2}\d{17,20})',
            r'vide\s*challan\s*(?:no\.?\s*)?([A-Z]{2}\d{17,20})',
            r'challan\s*([A-Z]{2}\d{17,20})',
            r'(?:bearing\s*)?(?:no\.?\s*)?([A-Z]{2}\d{17,20})\s*has\s*been\s*issued',
            r'challan\s*(?:number\s*)?([A-Z]{2}\d{14,20})',  # Flexible length for different states
            
            # Payment reference and receipt patterns
            r'challan\s*(?:reference\s*)?(?:number\s*)?[:\s]*([A-Z0-9]{8,20})',  # 3805F892F8
            r'(?:reference\s*)?(?:number\s*)?([A-Z0-9]{8,20})\s*for\s*payment',
            r'challan\s*(?:number\s*)?[:\s]*([A-Z]{2}\d{15,20})',  # HR469696231012033163
            r'(?:for\s*)?([A-Z]{2}[A-Z0-9]{10,20})\s*has\s*been\s*received',  # MPTURN150520240010822
            r'payment.*?for\s*([A-Z]{2}[A-Z0-9]{10,20})',
            r'challan\s*(?:no\.?\s*|number\s*)?[:\s]*([A-Z0-9]{10,25})',  # Generic alphanumeric
            
            # NEW: Patterns for missing examples
            r'vide\s*challan\s*(?:no\.?\s*)?(\d{8,12})',  # "vide challan No.57527311"
            r'challan\s*(?:no\.?\s*)?(\d{8,12})\b',  # Simple numeric challans
            r'challan\s*([A-Z]{2}\d{10,20})\s*issued',  # "challan HR67070221005165119 issued"
            r'a\s*challan\s*([A-Z]{2}\d{10,20})\s*issued',  # "A challan GJ4160807230909053094 issued"
            r'(?:challan\s*)?([A-Z]{2}\d{10,20})\s*issued\s*against',  # Issued against pattern
        ]

        self.vehicle_number_patterns = [
            r'vehicle\s*no\.?\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',  # HR87K5231, DL10SS4997
            r'vehicle\s*(?:number\s*)?[:\s]*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'against\s*your\s*vehicle\s*(?:number\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'for\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'by\s*your\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'vehicle\s*(?:registration\s*)?(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            
            # NEW: Patterns for missing examples
            r'issued\s*against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',  # "issued against HR51BM6192"
            r'against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',  # Simple "against HR51BM6192"
        ]

        # ENHANCED: Challan Fine/Amount Patterns
        self.challan_fine_patterns = [
            # Traditional fine patterns
            r'fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'pay\s*fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'penalty\s*(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[/-]*\s*fine',
            r'fine\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            
            # Payment and amount patterns
            r'payment\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'for\s*payment\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'total\s*(?:challan\s*)?amount[:\s]*rs?\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'total\s*(?:challan\s*)?amount[:\s]*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount[:\s]*(\d+(?:,\d{3})*(?:\.\d{1,2})?)(?:\s*rs?\.?)?(?:\s*[.-]|$)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*has\s*been\s*(?:initiated|received)',
            
            # NEW: Patterns for missing examples (without rs./Rs.)
            r'the\s*total\s*challan\s*amount\s*is\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',  # "The total challan amount is 500"
            r'challan\s*amount\s*is\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*DDCSMS',  # "fine of Rs.1000.00 DDCSMS"
        ]

        self.payment_link_patterns = [
            r'(https?://[^\s]+)',
            r'click\s*(https?://[^\s]+)',
            r'visit\s*(https?://[^\s]+)',
            r'logon\s*to\s*(https?://[^\s]+)',
            r'(https?://[a-zA-Z0-9.-]+[^\s]*)',
            r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            
            # NEW: Patterns for missing examples
            r'click\s*here:\s*(https?://[^\s]+)',  # "Click here: https://sama.live/..."
            r'visit:\s*(https?://[^\s]+)',  # "visit: https://bit.ly/..."
        ]

        # --- ENHANCED: Challan Message Indicators ---
        self.challan_indicators = [
            r'\bchallan\b',
            r'\btraffic\s*violation\b',
            r'\btraffic\s*fine\b',
            r'\btraffic\s*police\b',
            r'\bvirtual\s*court\b',
            r'\bvcourts\b',
            r'\bmorth\b',
            r'\bjupitice\b',
            r'\bpending\s*challan\b',
            r'\btraffic\s*challan\b',
            r'\bfine\s*of\s*rs\b',
            r'\bpay\s*fine\b',
            r'\bviolation\b',
            r'\bifms\b',
            r'\bmptreasury\b',
            r'\bpayment.*challan\b',
            r'\bchallan.*payment\b',
            r'\breference\s*number\b',
            r'\bchallan\s*receipt\b',
            r'\bsuccessfully\s*done\b',
            r'\bhas\s*been\s*received\b',
            r'\bhas\s*been\s*initiated\b',
            
            # NEW: Missing indicators
            r'\bonline\s*lok\s*adalat\b',  # "Online Lok Adalat"
            r'\bsama\.live\b',  # Sama platform
            r'\btraffic\s*violations\b',  # "Traffic violations"
            r'\bfound\s*actionable\b',  # "found actionable"
            r'\bissued\s*against\b',  # "issued against"
            r'\bnotice\s*branch\b',  # "NOTICE BRANCH"
            r'\bddcsms\b',  # Message ending indicator
        ]

        # --- ENHANCED: Challan Status Indicators ---
        self.challan_status_patterns = {
            'issued': [
                r'has\s*been\s*issued',
                r'is\s*sent\s*to\s*virtual\s*court',
                r'found\s*actionable',
                r'challan\s*(?:bearing\s*)?no',
                r'you\s*will\s*shortly\s*receive',
                r'has\s*been\s*initiated',
                # NEW: Additional issued patterns
                r'issued\s*against',
                r'a\s*challan.*issued',
                r'invites\s*you\s*to\s*pay',
            ],
            'pending': [
                r'pending\s*against',
                r'challan\s*pending',
                r'click\s*here\s*to\s*view',
                r'view\s*your\s*challan',
                r'pay\s*fine',
                r'make\s*the\s*payment',
                # NEW: Additional pending patterns
                r'online\s*lok\s*adalat',
                r'click\s*here:',
                r'may\s*pay\s*fine',
            ],
            'paid': [
                r'payment.*has\s*been\s*received',
                r'successfully\s*done',
                r'payment.*successful',
                r'challan\s*payment.*done',
                r'has\s*been\s*received.*kindly',
            ]
        }

        # --- ENHANCED: Authority/Department Patterns ---
        self.traffic_authority_patterns = {
            'Delhi Traffic Police': [r'delhi\s*traffic\s*police', r'notice\s*branch\s*delhi\s*traffic'],
            'Mumbai Traffic Police': [r'mumbai\s*traffic\s*police'],
            'Faridabad Traffic Police': [r'faridabad\s*traffic\s*police'],
            'Surat City Traffic Police': [r'surat\s*city\s*traffic\s*police'],
            'Maharashtra Police': [r'maharashtra\s*police'],
            'MoRTH': [r'\bmorth\b', r'ministry\s*of.*transport'],
            'Jupitice': [r'\bjupitice\b'],
            'Virtual Court': [r'virtual\s*court', r'vcourts'],
            'Parivahan': [r'parivahan'],
            'State Transport': [r'state\s*transport'],
            'iFMS': [r'\bifms\b'],
            'MP Treasury': [r'\bmptreasury\b', r'mp\s*treasury'],
            'MP Traffic': [r'mpturn\d+', r'mp.*traffic'],
            
            # NEW: Missing authorities
            'Sama Platform': [r'sama\.live', r'sama\s*platform'],
            'Online Lok Adalat': [r'online\s*lok\s*adalat'],
        }

        # --- Bank/Lender Name Patterns ---
        self.bank_patterns = {
            'IDFC FIRST Bank': [r'idfc\s*first\s*bank', r'idfc'],
            'Axis Bank': [r'axis\s*bank', r'axisbk'],
            'HDFC Bank': [r'hdfc\s*bank', r'hdfc'],
            'SBI': [r'sbi\b', r'state\s*bank'],
            'ICICI Bank': [r'icici\s*bank', r'icici'],
            'Kotak Bank': [r'kotak\s*bank', r'kotak'],
            'Chola Finance': [r'chola\s*(?:home\s*)?loans?', r'cholamandalam', r'chfl'],
            'Bajaj Finance': [r'bajaj\s*finance', r'bajaj'],
            'Bike Bazaar Finance': [r'bike\s*bazaar\s*finance'],
            'Fullerton India': [r'fullerton', r'fullertonv3'],
            'Mahindra Finance': [r'mahindra\s*finance'],
            'Tata Capital': [r'tata\s*capital'],
            'L&T Finance': [r'l&t\s*finance', r'l\s*&\s*t'],
            'Hero FinCorp': [r'hero\s*fincorp'],
            'TVS Credit': [r'tvs\s*credit']
        }

        # --- Account Number Patterns ---
        self.account_number_patterns = [
            r'loan\s*a[/c]*[:\s]*(\d{6,20})',
            r'loan\s*a[/c]*[:\s]*([A-Z0-9]{6,20})',
            r'account\s*(?:number|no)[:\s]*(\d{6,20})',
            r'account\s*(?:number|no)[:\s]*([A-Z0-9]{6,20})',
            r'loan\s*account[:\s]*(\d{6,20})',
            r'loan\s*account[:\s]*([A-Z0-9]{6,20})',
            r'a[/c]*[:\s]*(\d{6,20})(?:\D|$)',
            r'a[/c]*[:\s]*([A-Z0-9]{6,20})(?:\D|$)',
            r'account[:\s]*(\d{6,20})(?:\D|$)',
            r'account[:\s]*([A-Z0-9]{6,20})(?:\D|$)'
        ]

        # --- EMI Message Indicators ---
        self.emi_indicators = [
            r'\bemi\b',
            r'\bloan\b',
            r'\binstallment\b',
            r'\binstalment\b',
            r'\bpayment\s*(?:due|pending|overdue)\b',
            r'\bdue\s*(?:date|amount)\b',
            r'\boverdue\b',
            r'\bbounce\s*charge\b',
            r'\boutstanding\s*(?:amount|balance)\b',
            r'\brepayment\b'
        ]

        # --- EMI EXCLUSION PATTERNS (For EMI Promotions/Offers) ---
        self.emi_exclusion_patterns = [
            r'\b(?:zero|0)%?\s*interest\b',
            r'\bno\s*cost\s*emi\b',
            r'\beasy\s*emi\s*options?\b',
            r'\bemi\s*starts?\s*from\b',
            r'\bemi\s*as\s*low\s*as\b',
            r'\bavail\s*emi\b',
            r'\bget\s*.*?emi\b',
            r'\bbuy\s*now\b',
            r'\bshop\s*now\b',
            r'\boffer\s*(?:valid|expires?)\b',
            r'\b(?:sale|offer|deal|discount)\b.*\bemi\b',
            r'\bemi\s*facility\s*available\b',
            r'\bconvert\s*to\s*emi\b',
            r'\bcashback\b',
            r'\b(?:special|festive|limited)\s*(?:offer|deal)\b'
        ]

        # --- General Keywords & Patterns for Confidence Scoring ---
        self.true_otp_patterns = [
            r'\b(otp|one[- ]?time[- ]?password|verification code|login code|registration code)\b',
            r'\b(enter\s*[\d-]+)\b',
            r'(\d{4,8})\s*is\s*your',
            r'valid\s*for\s*\d+\s*minutes'
        ]
        
        # --- Company & Service Keywords for OTP ---
        self.company_patterns = {
            'Google': [r'\bgoogle\b'], 'Google Pay': [r'\bgoogle pay\b'],
            'Axis Bank': [r'\baxis bank\b'], 'Instagram': [r'\binstagram\b'],
            'Discord': [r'\bdiscord\b'], 'Signal': [r'\bsignal\b'],
            'Aarogya Setu': [r'aarogya setu'],
            'Amazon': [r'\bamazon\b'], 'Flipkart': [r'\bflipkart\b'],
            'Paytm': [r'\bpaytm\b'], 'Swiggy': [r'\bswiggy\b'],
            'HDFC': [r'\bhdfc\b'], 'SBI': [r'\bsbi\b'], 'ICICI': [r'\bicici\b'],
            'UTS Mobile Ticket': [r'\buts\s*mobile\s*ticket\b', r'\buts\b'],
            'CRIS': [r'\bcris\b'], 'Dream11': [r'\bdream11\b'], 'Zupee': [r'\bzupee\b'],
            'Meesho': [r'\bmeesho\b'], 'AJIO': [r'\bajio\b'], 'Myntra': [r'\bmyntra\b'],
            'Zomato': [r'\bzomato\b'], 'Ola': [r'\bola\b'], 'Uber': [r'\buber\b'],
            'Jio': [r'\bjio\b'], 'Airtel': [r'\bairtel\b'], 'Vi': [r'\bvi\b'],
            'WhatsApp': [r'\bwhatsapp\b'], 'Facebook': [r'\bfacebook\b'],
        }

        # --- STRONG EXCLUSION PATTERNS for OTP ---
        self.strong_exclusion_patterns = [
            r'order\s*#\s*\d+',
            r'order\s*(?:number|no|id)\s*[:\s]*\w+',
            r'use\s*code\s*[A-Z]+\d+',
            r'account\s*balance',
            r'bal\s*:\s*rs',
            r'tracking\s*number',
            r'flight\s*number',
            r'call\s*us\s*at',
            r'promo\s*code',
        ]

        # --- Compile all patterns for performance ---
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for better performance"""
        self.compiled_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.otp_patterns]
        self.compiled_true_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.true_otp_patterns]
        self.compiled_strong_exclusions = [re.compile(p, re.IGNORECASE) for p in self.strong_exclusion_patterns]
        
        # EMI pattern compilation
        self.compiled_emi_amount_patterns = [re.compile(p, re.IGNORECASE) for p in self.emi_amount_patterns]
        self.compiled_emi_due_date_patterns = [re.compile(p, re.IGNORECASE) for p in self.emi_due_date_patterns]
        self.compiled_account_number_patterns = [re.compile(p, re.IGNORECASE) for p in self.account_number_patterns]
        self.compiled_emi_indicators = [re.compile(p, re.IGNORECASE) for p in self.emi_indicators]
        self.compiled_emi_exclusions = [re.compile(p, re.IGNORECASE) for p in self.emi_exclusion_patterns]
        
        # Challan pattern compilation
        self.compiled_challan_number_patterns = [re.compile(p, re.IGNORECASE) for p in self.challan_number_patterns]
        self.compiled_vehicle_number_patterns = [re.compile(p, re.IGNORECASE) for p in self.vehicle_number_patterns]
        self.compiled_challan_fine_patterns = [re.compile(p, re.IGNORECASE) for p in self.challan_fine_patterns]
        self.compiled_payment_link_patterns = [re.compile(p, re.IGNORECASE) for p in self.payment_link_patterns]
        self.compiled_challan_indicators = [re.compile(p, re.IGNORECASE) for p in self.challan_indicators]
        
        # Challan status patterns
        self.compiled_challan_status_patterns = {}
        for status, patterns in self.challan_status_patterns.items():
            self.compiled_challan_status_patterns[status] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Company patterns
        self.compiled_company_patterns = {}
        for company, patterns in self.company_patterns.items():
            self.compiled_company_patterns[company] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self.compiled_bank_patterns = {}
        for bank, patterns in self.bank_patterns.items():
            self.compiled_bank_patterns[bank] = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Traffic authority patterns
        self.compiled_traffic_authority_patterns = {}
        for authority, patterns in self.traffic_authority_patterns.items():
            self.compiled_traffic_authority_patterns[authority] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def clean_text(self, text: str) -> str:
        if pd.isna(text): return ""
        return str(text).strip()

    # --- OTP PARSING METHODS (Existing) ---
    def extract_otp_code(self, text: str) -> Optional[str]:
        for pattern in self.compiled_otp_patterns:
            match = pattern.search(text)
            if match:
                return re.sub(r'[- ]', '', match.group(1))
        
        if any(p.search(text.lower()) for p in self.compiled_true_otp_patterns):
            potential_otps = re.findall(r'\b\d{4,8}\b', text)
            if potential_otps:
                return potential_otps[0]
        return None

    def extract_company_name(self, text: str, sender_name: str = "") -> Optional[str]:
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for company, patterns in self.compiled_company_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return company
        return None

    def calculate_otp_confidence_score(self, text: str) -> int:
        score = 0
        text_lower = text.lower()
        
        if any(p.search(text_lower) for p in self.compiled_strong_exclusions):
            return 0

        otp_code = self.extract_otp_code(text)
        if otp_code:
            score += 50
        
        if any(p.search(text_lower) for p in self.compiled_true_otp_patterns):
            score += 25
        
        if self.extract_company_name(text_lower):
            score += 15
        
        if "don't share" in text_lower or "do not share" in text_lower or "valid for" in text_lower:
            score += 10

        return max(0, min(100, score))

    # --- EMI PARSING METHODS (Existing) ---
    def extract_emi_amount(self, text: str) -> Optional[str]:
        """Extract EMI amount from the message"""
        for pattern in self.compiled_emi_amount_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                return amount
        return None

    def extract_emi_due_date(self, text: str) -> Optional[str]:
        """Extract EMI due date from the message"""
        for pattern in self.compiled_emi_due_date_patterns:
            match = pattern.search(text)
            if match:
                date_str = match.group(1)
                # Normalize the date format
                return self.normalize_date(date_str)
        return None

    def normalize_date(self, date_str: str) -> str:
        """Normalize various date formats to a standard format"""
        date_str = date_str.strip()
        
        # Handle month abbreviations like Jul'2024
        month_abbrev_match = re.match(r"([a-z]{3})'?(\d{4})", date_str, re.IGNORECASE)
        if month_abbrev_match:
            month_abbrev = month_abbrev_match.group(1).title()
            year = month_abbrev_match.group(2)
            return f"{month_abbrev} {year}"
        
        # Handle full month names like July 2024
        month_full_match = re.match(r"([a-z]{3,9})\s*(\d{4})", date_str, re.IGNORECASE)
        if month_full_match:
            month = month_full_match.group(1).title()
            year = month_full_match.group(2)
            return f"{month} {year}"
        
        # Handle DD/MM/YYYY or DD-MM-YYYY formats
        date_match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", date_str)
        if date_match:
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = "20" + year
            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
        
        return date_str

    def extract_bank_name(self, text: str, sender_name: str = "") -> Optional[str]:
        """Extract bank/lender name from the message"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for bank, patterns in self.compiled_bank_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return bank
        return None

    def extract_account_number(self, text: str) -> Optional[str]:
        """Extract account number from the message"""
        text_upper = text.upper()
        for pattern in self.compiled_account_number_patterns:
            match = pattern.search(text_upper)
            if match:
                account_num = match.group(1)
                # Additional validation to ensure it's a valid account number
                # Must have at least some digits and reasonable length
                if any(c.isdigit() for c in account_num) and 6 <= len(account_num) <= 20:
                    # Check if it's not a common word that might match
                    if not account_num.isalpha() or len(account_num) <= 8:
                        return account_num
        return None

    def calculate_emi_confidence_score(self, text: str) -> int:
        """Calculate confidence score for EMI messages"""
        score = 0
        text_lower = text.lower()
        
        # Check for EMI promotion exclusions first
        if any(p.search(text_lower) for p in self.compiled_emi_exclusions):
            return 0  # Immediately reject promotional EMI messages
        
        # Check for EMI indicators
        emi_indicator_count = sum(1 for p in self.compiled_emi_indicators if p.search(text_lower))
        score += emi_indicator_count * 20
        
        # Check if EMI amount is found
        if self.extract_emi_amount(text):
            score += 30
        
        # Check if bank name is found
        if self.extract_bank_name(text):
            score += 20
        
        # Check if account number is found
        if self.extract_account_number(text):
            score += 15
        
        # Check if due date is found
        if self.extract_emi_due_date(text):
            score += 15
        
        # Additional keywords that indicate EMI reminders
        reminder_keywords = ['pending', 'overdue', 'bounce', 'unpaid', 'not paid', 'dishonour']
        if any(keyword in text_lower for keyword in reminder_keywords):
            score += 10
        
        return max(0, min(100, score))

    def is_emi_message(self, text: str) -> bool:
        """Check if message contains EMI-related indicators"""
        text_lower = text.lower()
        return any(p.search(text_lower) for p in self.compiled_emi_indicators)

    # --- ENHANCED: TRAFFIC CHALLAN PARSING METHODS ---
    def extract_challan_number(self, text: str) -> Optional[str]:
        """Extract challan number from the message - Enhanced for missing patterns"""
        text_upper = text.upper()
        
        for pattern in self.compiled_challan_number_patterns:
            match = pattern.search(text_upper)
            if match:
                challan_num = match.group(1)
                # Enhanced validation for different challan number formats
                if self.is_valid_challan_number(challan_num):
                    return challan_num
        
        return None

    def is_valid_challan_number(self, challan_num: str) -> bool:
        """Enhanced validation for challan numbers including new formats"""
        challan_num = challan_num.strip()
        
        # Traditional state-based challan numbers (DL116709240411110024, HR469696231012033163)
        if len(challan_num) >= 16 and challan_num[:2].isalpha() and challan_num[2:].isdigit():
            return True
        
        # Medium length state-based (HR67070221005165119, GJ4160807230909053094)
        if 12 <= len(challan_num) <= 20 and challan_num[:2].isalpha() and challan_num[2:].isdigit():
            return True
        
        # Short numeric challans (57527311 - 8 digits)
        if 8 <= len(challan_num) <= 12 and challan_num.isdigit():
            return True
        
        # Payment reference numbers (3805F892F8)
        if 8 <= len(challan_num) <= 12 and re.match(r'^[A-Z0-9]+$', challan_num):
            return True
        
        # State + alphanumeric formats (MPTURN150520240010822)
        if len(challan_num) >= 10 and re.match(r'^[A-Z]{2,6}[A-Z0-9]+$', challan_num):
            return True
        
        # Generic alphanumeric format (minimum 8 characters)
        if len(challan_num) >= 8 and re.match(r'^[A-Z0-9]+$', challan_num):
            # Ensure it has at least some letters and numbers
            has_letters = any(c.isalpha() for c in challan_num)
            has_numbers = any(c.isdigit() for c in challan_num)
            return has_letters and has_numbers
        
        return False

    def extract_vehicle_number(self, text: str) -> Optional[str]:
        """Extract vehicle number from the message - Enhanced for missing patterns"""
        text_upper = text.upper()
        for pattern in self.compiled_vehicle_number_patterns:
            match = pattern.search(text_upper)
            if match:
                vehicle_num = match.group(1)
                # Additional validation for Indian vehicle number format
                if self.is_valid_vehicle_number(vehicle_num):
                    return vehicle_num
        return None

    def is_valid_vehicle_number(self, vehicle_num: str) -> bool:
        """Validate Indian vehicle number format"""
        # Remove spaces and convert to uppercase
        vehicle_num = vehicle_num.replace(' ', '').upper()
        
        # Indian vehicle number formats:
        # XX##XXXX or XX##X####
        patterns = [
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4}$',  # HR87K5231, DL10SS4997, HR51BM6192, GJ05RK8881
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$',  # GJ05CX0282
        ]
        
        return any(re.match(pattern, vehicle_num) for pattern in patterns)

    def extract_challan_fine_amount(self, text: str) -> Optional[str]:
        """Extract fine amount from the challan message - Enhanced for payment patterns"""
        for pattern in self.compiled_challan_fine_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                # Additional validation for reasonable amount ranges
                try:
                    amount_float = float(amount)
                    if 1 <= amount_float <= 100000:  # Reasonable fine range
                        return amount
                except ValueError:
                    continue
        return None

    def extract_payment_link(self, text: str) -> Optional[str]:
        """Extract payment link from the message - Enhanced for missing patterns"""
        for pattern in self.compiled_payment_link_patterns:
            match = pattern.search(text)
            if match:
                link = match.group(1) if match.group(1).startswith('http') else match.group(0)
                # Clean the link of any trailing punctuation
                link = re.sub(r'[.,;)\]}\s]*$', '', link)
                return link
        return None

    def extract_traffic_authority(self, text: str, sender_name: str = "") -> Optional[str]:
        """Extract traffic authority/department from the message - Enhanced"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for authority, patterns in self.compiled_traffic_authority_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return authority
        return None

    def determine_challan_status(self, text: str) -> str:
        """Determine challan status - Enhanced with new patterns"""
        text_lower = text.lower()
        
        # Check for payment completion status first
        for pattern in self.compiled_challan_status_patterns['paid']:
            if pattern.search(text_lower):
                return 'paid'
        
        # Check for pending payment indicators (including new patterns)
        for pattern in self.compiled_challan_status_patterns['pending']:
            if pattern.search(text_lower):
                return 'pending'
        
        # Check for issued status indicators
        for pattern in self.compiled_challan_status_patterns['issued']:
            if pattern.search(text_lower):
                return 'issued'
        
        # Default to issued if unclear
        return 'issued'

    def calculate_challan_confidence_score(self, text: str) -> int:
        """Calculate confidence score for traffic challan messages - Enhanced"""
        score = 0
        text_lower = text.lower()
        
        # Check for challan indicators - Enhanced scoring
        challan_indicator_count = sum(1 for p in self.compiled_challan_indicators if p.search(text_lower))
        score += challan_indicator_count * 12  # Reduced individual weight, more indicators
        
        # Check if challan number is found - Higher weight for stronger identifier
        if self.extract_challan_number(text):
            score += 45
        
        # Check if vehicle number is found
        if self.extract_vehicle_number(text):
            score += 25
        
        # Check if fine amount is found
        if self.extract_challan_fine_amount(text):
            score += 20  # Increased weight for amount
        
        # Check if payment link is found
        if self.extract_payment_link(text):
            score += 10
        
        # Check if traffic authority is found
        if self.extract_traffic_authority(text):
            score += 15  # Increased weight for authority
        
        # Enhanced keywords for different message types
        traffic_keywords = ['violation', 'traffic police', 'virtual court', 'actionable', 'disposal', 'issued against', 'found actionable']
        payment_keywords = ['payment', 'receipt', 'reference number', 'initiated', 'received', 'online lok adalat', 'sama.live']
        
        traffic_matches = sum(1 for keyword in traffic_keywords if keyword in text_lower)
        payment_matches = sum(1 for keyword in payment_keywords if keyword in text_lower)
        
        score += traffic_matches * 8
        score += payment_matches * 8
        
        # Boost score for payment-related messages and new platforms
        if any(keyword in text_lower for keyword in ['ifms', 'mptreasury', 'successfully done', 'sama.live', 'online lok adalat']):
            score += 15
        
        return max(0, min(100, score))

    def is_challan_message(self, text: str) -> bool:
        """Check if message contains challan-related indicators - Enhanced"""
        text_lower = text.lower()
        
        # Primary indicators
        if any(p.search(text_lower) for p in self.compiled_challan_indicators):
            return True
        
        # Secondary indicators - payment references and receipts
        secondary_patterns = [
            r'reference\s*number.*payment',
            r'challan.*receipt',
            r'traffic.*payment',
            r'violation.*amount',
            r'issued\s*against',
            r'online\s*lok\s*adalat',
        ]
        
        return any(re.search(pattern, text_lower) for pattern in secondary_patterns)

    def parse_challan_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse traffic challan information from the message - Enhanced"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        
        confidence_score = self.calculate_challan_confidence_score(combined_text)
        
        if confidence_score >= 40:  # Lowered threshold further for better detection
            result = {
                'status': 'parsed',
                'message_type': 'challan',
                'confidence_score': confidence_score,
                'challan_number': self.extract_challan_number(clean_message),
                'vehicle_number': self.extract_vehicle_number(clean_message),
                'fine_amount': self.extract_challan_fine_amount(clean_message),
                'payment_link': self.extract_payment_link(clean_message),
                'traffic_authority': self.extract_traffic_authority(clean_message, sender_name),
                'challan_status': self.determine_challan_status(clean_message),
                'raw_message': message,
            }
            return result
        
        return {
            'status': 'rejected',
            'message_type': 'challan',
            'reason': 'Message did not meet the confidence threshold for a traffic challan.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    def parse_emi_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse EMI-specific information from the message"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        
        confidence_score = self.calculate_emi_confidence_score(combined_text)
        
        if confidence_score >= 50:  # Threshold for EMI messages
            result = {
                'status': 'parsed',
                'message_type': 'emi',
                'confidence_score': confidence_score,
                'emi_amount': self.extract_emi_amount(clean_message),
                'emi_due_date': self.extract_emi_due_date(clean_message),
                'bank_name': self.extract_bank_name(clean_message, sender_name),
                'account_number': self.extract_account_number(clean_message),
                'raw_message': message,
            }
            return result
        
        return {
            'status': 'rejected',
            'message_type': 'emi',
            'reason': 'Message did not meet the confidence threshold for an EMI reminder.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    def parse_single_message(self, message: str, sender_name: str = "", message_type: str = "auto") -> Dict:
        """Parse a single message for OTP, EMI, or challan content - Enhanced"""
        clean_message = self.clean_text(message)
        
        if message_type == "auto":
            # Auto-detect message type based on content with enhanced logic
            challan_indicators = sum(1 for p in self.compiled_challan_indicators if p.search(clean_message.lower()))
            emi_indicators = sum(1 for p in self.compiled_emi_indicators if p.search(clean_message.lower()))
            
            # Enhanced auto-detection logic
            if challan_indicators > 0 or self.extract_challan_number(clean_message) or self.extract_vehicle_number(clean_message):
                return self.parse_challan_message(message, sender_name)
            elif emi_indicators > 0 and not any(p.search(clean_message.lower()) for p in self.compiled_emi_exclusions):
                return self.parse_emi_message(message, sender_name)
            else:
                return self.parse_otp_message(message, sender_name)
        elif message_type == "challan":
            return self.parse_challan_message(message, sender_name)
        elif message_type == "emi":
            return self.parse_emi_message(message, sender_name)
        elif message_type == "otp":
            return self.parse_otp_message(message, sender_name)
        else:
            return {'status': 'error', 'reason': 'Invalid message type specified'}

    def parse_otp_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse OTP-specific information from the message (existing functionality)"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        
        confidence_score = self.calculate_otp_confidence_score(combined_text)
        
        if confidence_score >= 50:
            otp_code = self.extract_otp_code(clean_message)
            if otp_code:
                result = {
                    'status': 'parsed',
                    'message_type': 'otp',
                    'confidence_score': confidence_score,
                    'otp_code': otp_code,
                    'company_name': self.extract_company_name(clean_message, sender_name),
                    'purpose': self.extract_purpose(clean_message),
                    'expiry_info': self.extract_expiry_time(clean_message),
                    'security_warnings': self.extract_security_warnings(clean_message),
                    'raw_message': message,
                }
                return result

        return {
            'status': 'rejected',
            'message_type': 'otp',
            'reason': 'Message did not meet the confidence threshold for an OTP.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    # --- EXISTING OTP HELPER METHODS (Keep unchanged) ---
    def extract_purpose(self, text: str) -> Optional[str]:
        """Extract purpose of OTP (existing method)"""
        purpose_patterns = {
            'Login': [r'\bto\s*(?:login|log\s*in|sign\s*in)\b', r'\bfor\s*(?:login|log\s*in|sign\s*in)\b'],
            'Verification': [r'\bto\s*(?:verify|verification)\b', r'\bfor\s*(?:verification|account\s*verification)\b'],
            'Transaction': [r'\bto\s*(?:complete|authorize)\s*(?:transaction|payment)\b'],
            'Payment': [r'for\s*payment'],
        }
        
        text_lower = text.lower()
        for purpose, patterns in purpose_patterns.items():
            if any(re.search(p, text_lower) for p in patterns):
                return purpose
        return None
        
    def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
        """Extract expiry time information (existing method)"""
        expiry_patterns = [
            r'\bvalid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bexpires?\s*in\s*(\d+)\s*(minutes?|mins?|min)\b',
        ]
        
        for pattern in expiry_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'duration': match.group(1),
                    'unit': match.group(2),
                    'full_text': match.group(0)
                }
        return None

    def extract_security_warnings(self, text: str) -> List[str]:
        """Extract security warnings (existing method)"""
        security_patterns = [r'\bdo\s*not\s*share\b', r'\bnever\s*share\b']
        warnings = []
        for pattern in security_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                warnings.append(match.group(0))
        return warnings

    def process_csv_file(self, input_file: str, output_file: str = None, message_type: str = "auto") -> Dict:
        """Process CSV file for OTP, EMI, and challan messages"""
        print("Enhanced Message Parser v8.0 - Analyzing Messages for OTP, EMI, and Traffic Challan Content")
        print("=" * 80)
        print("Loading CSV file...")
        start_time = time.time()
        
        try:
            df = pd.read_csv(input_file, dtype=str)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return None
        
        print(f"Loaded {len(df):,} rows in {time.time() - start_time:.2f} seconds")
        
        if 'message' not in df.columns:
            print("Error: 'message' column not found")
            return None
        
        if 'sender_name' not in df.columns:
            print("Warning: 'sender_name' column not found. Using empty values.")
            df['sender_name'] = ""
        
        print(f"Analyzing {len(df):,} messages for content...")
        
        parsed_messages = []
        rejected_messages = []
        
        parse_start = time.time()
        batch_size = 1000
        total_messages = len(df)
        
        for i in range(0, total_messages, batch_size):
            end_idx = min(i + batch_size, total_messages)
            
            for idx in range(i, end_idx):
                row = df.iloc[idx]
                message = row['message'] if pd.notna(row['message']) else ""
                sender = row['sender_name'] if pd.notna(row['sender_name']) else ""
                
                parsed_result = self.parse_single_message(message, sender, message_type)
                parsed_result['original_index'] = idx
                
                if parsed_result['status'] == 'parsed':
                    parsed_messages.append(parsed_result)
                else:
                    rejected_messages.append(parsed_result)
            
            progress = (end_idx / total_messages) * 100
            elapsed = time.time() - parse_start
            rate = end_idx / elapsed if elapsed > 0 else 0
            
            if (end_idx % 10000 == 0) or (end_idx == total_messages):
                print(f"Progress: {progress:.1f}% ({end_idx:,}/{total_messages:,}) | "
                      f"Rate: {rate:.0f} msgs/sec | "
                      f"Parsed: {len(parsed_messages):,} | "
                      f"Rejected: {len(rejected_messages):,}")
        
        parse_time = time.time() - parse_start
        print(f"\nAnalysis completed in {parse_time/60:.1f} minutes")
        
        # Separate messages by type
        otp_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'otp']
        emi_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'emi']
        challan_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'challan']
        
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'total_parsed_messages': len(parsed_messages),
                'otp_messages_found': len(otp_messages),
                'emi_messages_found': len(emi_messages),
                'challan_messages_found': len(challan_messages),
                'rejected_messages': len(rejected_messages),
                'detection_rate': round((len(parsed_messages) / total_messages) * 100, 2),
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '8.0_enhanced_missing_pattern_detection'
            },
            'summary_statistics': {
                'otp_stats': self.generate_otp_summary_stats(otp_messages),
                'emi_stats': self.generate_emi_summary_stats(emi_messages),
                'challan_stats': self.generate_challan_summary_stats(challan_messages)
            },
            'otp_messages': otp_messages,
            'emi_messages': emi_messages,
            'challan_messages': challan_messages,
            'sample_rejected_messages': rejected_messages[:10]
        }
        
        self.display_parsing_summary(results)
        
        if output_file is None:
            base_name = input_file.replace('.csv', '')
            output_file = f"{base_name}_parsed_messages.json"
        
        print(f"\nSaving results to: {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("Results saved successfully!")
        except Exception as e:
            print(f"Error saving results: {e}")
            return None
        
        return results

    def generate_otp_summary_stats(self, otp_messages: List[Dict]) -> Dict:
        """Generate summary statistics for OTP messages"""
        if not otp_messages:
            return {}
        
        companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
        company_counts = {}
        for company in companies:
            company_counts[company] = company_counts.get(company, 0) + 1
        
        purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
        purpose_counts = {}
        for purpose in purposes:
            purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        
        confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            'total_count': len(otp_messages),
            'distributions': {
                'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
            },
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
                'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
                'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
            }
        }

    def generate_emi_summary_stats(self, emi_messages: List[Dict]) -> Dict:
        """Generate summary statistics for EMI messages"""
        if not emi_messages:
            return {}
        
        banks = [msg.get('bank_name') for msg in emi_messages if msg.get('bank_name')]
        bank_counts = {}
        for bank in banks:
            bank_counts[bank] = bank_counts.get(bank, 0) + 1
        
        # Analyze EMI amounts
        amounts = []
        for msg in emi_messages:
            amount_str = msg.get('emi_amount')
            if amount_str:
                try:
                    amount = float(amount_str.replace(',', ''))
                    amounts.append(amount)
                except ValueError:
                    continue
        
        confidence_scores = [msg.get('confidence_score', 0) for msg in emi_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        amount_stats = {}
        if amounts:
            amount_stats = {
                'average_amount': round(sum(amounts) / len(amounts), 2),
                'min_amount': min(amounts),
                'max_amount': max(amounts),
                'total_emi_value': sum(amounts)
            }
        
        return {
            'total_count': len(emi_messages),
            'distributions': {
                'top_banks': dict(sorted(bank_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            },
            'amount_statistics': amount_stats,
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
                'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
                'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
                'messages_with_amount': sum(1 for msg in emi_messages if msg.get('emi_amount')),
                'messages_with_bank': sum(1 for msg in emi_messages if msg.get('bank_name')),
                'messages_with_account': sum(1 for msg in emi_messages if msg.get('account_number')),
                'messages_with_due_date': sum(1 for msg in emi_messages if msg.get('emi_due_date')),
            }
        }

    def generate_challan_summary_stats(self, challan_messages: List[Dict]) -> Dict:
        """Generate summary statistics for traffic challan messages - Enhanced"""
        if not challan_messages:
            return {}
        
        # Authority distribution
        authorities = [msg.get('traffic_authority') for msg in challan_messages if msg.get('traffic_authority')]
        authority_counts = {}
        for authority in authorities:
            authority_counts[authority] = authority_counts.get(authority, 0) + 1
        
        # Status distribution - Enhanced with paid status
        statuses = [msg.get('challan_status') for msg in challan_messages if msg.get('challan_status')]
        status_counts = {}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Analyze fine amounts
        fine_amounts = []
        for msg in challan_messages:
            amount_str = msg.get('fine_amount')
            if amount_str:
                try:
                    amount = float(amount_str.replace(',', ''))
                    fine_amounts.append(amount)
                except ValueError:
                    continue
        
        confidence_scores = [msg.get('confidence_score', 0) for msg in challan_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        fine_stats = {}
        if fine_amounts:
            fine_stats = {
                'average_fine': round(sum(fine_amounts) / len(fine_amounts), 2),
                'min_fine': min(fine_amounts),
                'max_fine': max(fine_amounts),
                'total_fine_value': sum(fine_amounts)
            }
        
        return {
            'total_count': len(challan_messages),
            'distributions': {
                'authorities': dict(sorted(authority_counts.items(), key=lambda x: x[1], reverse=True)),
                'status_types': dict(sorted(status_counts.items(), key=lambda x: x[1], reverse=True)),
            },
            'fine_statistics': fine_stats,
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
                'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
                'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
                'messages_with_challan_number': sum(1 for msg in challan_messages if msg.get('challan_number')),
                'messages_with_vehicle_number': sum(1 for msg in challan_messages if msg.get('vehicle_number')),
                'messages_with_fine_amount': sum(1 for msg in challan_messages if msg.get('fine_amount')),
                'messages_with_payment_link': sum(1 for msg in challan_messages if msg.get('payment_link')),
            }
        }

    def display_parsing_summary(self, results: Dict):
        """Display comprehensive parsing summary for OTP, EMI, and challan"""
        metadata = results['metadata']
        otp_stats = results.get('summary_statistics', {}).get('otp_stats', {})
        emi_stats = results.get('summary_statistics', {}).get('emi_stats', {})
        challan_stats = results.get('summary_statistics', {}).get('challan_stats', {})
        
        print("\n" + "="*80)
        print("ENHANCED MESSAGE PARSING RESULTS SUMMARY v8.0")
        print("="*80)
        
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"Total Parsed Messages: {metadata['total_parsed_messages']:,}")
        print(f"  - OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"  - EMI Messages Found: {metadata['emi_messages_found']:,}")
        print(f"  - Challan Messages Found: {metadata['challan_messages_found']:,}")
        print(f"Messages Rejected: {metadata['rejected_messages']:,}")
        print(f"Overall Detection Rate: {metadata['detection_rate']}%")
        
        # OTP Summary
        if otp_stats and otp_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("OTP MESSAGES SUMMARY")
            print("="*60)
            
            distributions = otp_stats.get('distributions', {})
            quality_metrics = otp_stats.get('quality_metrics', {})
            
            print("Top Companies/Services:")
            for company, count in list(distributions.get('top_companies', {}).items())[:5]:
                percentage = (count / otp_stats['total_count']) * 100
                print(f"  {company}: {count:,} ({percentage:.1f}%)")
            
            print(f"\nOTP Quality Metrics:")
            print(f"  Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")
            print(f"  High Confidence (>=80): {quality_metrics.get('high_confidence_messages', 0)}")
        
        # EMI Summary
        if emi_stats and emi_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("EMI MESSAGES SUMMARY")
            print("="*60)
            
            distributions = emi_stats.get('distributions', {})
            quality_metrics = emi_stats.get('quality_metrics', {})
            amount_stats = emi_stats.get('amount_statistics', {})
            
            print("Top Banks/Lenders:")
            for bank, count in list(distributions.get('top_banks', {}).items())[:5]:
                percentage = (count / emi_stats['total_count']) * 100
                print(f"  {bank}: {count:,} ({percentage:.1f}%)")
            
            if amount_stats:
                print(f"\nEMI Amount Statistics:")
                print(f"  Average EMI: Rs.{amount_stats.get('average_amount', 0):,.2f}")
                print(f"  Total EMI Value: Rs.{amount_stats.get('total_emi_value', 0):,.2f}")
            
            print(f"\nEMI Data Completeness:")
            print(f"  Messages with Amount: {quality_metrics.get('messages_with_amount', 0)}/{emi_stats['total_count']}")
            print(f"  Messages with Bank: {quality_metrics.get('messages_with_bank', 0)}/{emi_stats['total_count']}")
        
        # Challan Summary - Enhanced
        if challan_stats and challan_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("TRAFFIC CHALLAN MESSAGES SUMMARY (ENHANCED)")
            print("="*60)
            
            distributions = challan_stats.get('distributions', {})
            quality_metrics = challan_stats.get('quality_metrics', {})
            fine_stats = challan_stats.get('fine_statistics', {})
            
            print("Traffic Authorities:")
            for authority, count in distributions.get('authorities', {}).items():
                percentage = (count / challan_stats['total_count']) * 100
                print(f"  {authority}: {count:,} ({percentage:.1f}%)")
            
            print("\nChallan Status Distribution:")
            for status, count in distributions.get('status_types', {}).items():
                percentage = (count / challan_stats['total_count']) * 100
                status_emoji = "Paid" if status == 'paid' else "Pending" if status == 'pending' else "Issued"
                print(f"  {status_emoji}: {count:,} ({percentage:.1f}%)")
            
            if fine_stats:
                print(f"\nFine Amount Statistics:")
                print(f"  Average Fine: Rs.{fine_stats.get('average_fine', 0):,.2f}")
                print(f"  Highest Fine: Rs.{fine_stats.get('max_fine', 0):,.2f}")
                print(f"  Total Fines: Rs.{fine_stats.get('total_fine_value', 0):,.2f}")
            
            print(f"\nChallan Data Completeness:")
            print(f"  Messages with Challan Number: {quality_metrics.get('messages_with_challan_number', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Vehicle Number: {quality_metrics.get('messages_with_vehicle_number', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Fine Amount: {quality_metrics.get('messages_with_fine_amount', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Payment Link: {quality_metrics.get('messages_with_payment_link', 0)}/{challan_stats['total_count']}")

    def test_enhanced_parser(self):
        """Comprehensive test suite for OTP, EMI, and challan parsing - Enhanced with MISSING examples"""
        print("--- Running Enhanced Parser Test Suite v8.0 ---")
        print("--- Testing MISSING PATTERNS from user examples ---")
        
        # OTP Test Cases (unchanged)
        otp_test_cases = [
            ("Thank you for your order #567890 from Zomato.", None, "otp"),
            ("Flash Sale! Get 50% off on orders above Rs. 1500. Use code SAVE50.", None, "otp"),
            ("Your account balance is INR 12,345.67 as of 29-Aug-2025.", None, "otp"),
            ("OTP for Aarogya Setu is 1357. Stay safe.", "1357", "otp"),
            ("Your Discord verification code is 887766", "887766", "otp"),
            ("Your Signal registration code is 246-810.", "246810", "otp"),
            ("123 456 is your Instagram login code. Don't share it.", "123456", "otp"),
        ]
        
        # EMI Test Cases (unchanged)
        emi_test_cases = [
            ("Dear Customer, EMI payment of Rs. 3406.00/- for Jul'2024 for your loan account RTMN2W000005200062 is not paid.", {
                "emi_amount": "3406.00",
                "emi_due_date": "Jul 2024",
                "account_number": "RTMN2W000005200062"
            }, "emi"),
            ("Your IDFC FIRST Bank Two-Wheeler loan EMI of Rs 2446, Loan a/c: 65689256, is still PENDING!", {
                "emi_amount": "2446",
                "bank_name": "IDFC FIRST Bank",
                "account_number": "65689256"
            }, "emi"),
            ("Get easy EMI options starting from just Rs 999! Shop now with 0% interest!", None, "emi"),
        ]
        
        # ENHANCED: Challan Test Cases with NEW MISSING EXAMPLES
        challan_test_cases = [
            # MISSING EXAMPLE 1: Maharashtra Police + Sama.live
            ("Maharashtra Police invites you to pay your Traffic Challan through the Online Lok Adalat, via Sama. Click here: https://sama.live/mnotice.php?caseid=MH41AW2969", {
                "traffic_authority": "Maharashtra Police",
                "payment_link": "https://sama.live/mnotice.php?caseid=MH41AW2969",
                "challan_status": "pending"
            }, "challan"),
            
            # MISSING EXAMPLE 2: Short numeric challan number
            ("Traffic violations by your Vehicle No.: HR87K5231 found actionable vide challan No.57527311. Click https://vcourts.gov.in and select department NOTICE BRANCH DELHI TRAFFIC D to see details and may pay fine of Rs.1000.00 DDCSMS", {
                "challan_number": "57527311",
                "vehicle_number": "HR87K5231",
                "fine_amount": "1000.00",
                "payment_link": "https://vcourts.gov.in",
                "traffic_authority": "Delhi Traffic Police",
                "challan_status": "pending"
            }, "challan"),
            
            # MISSING EXAMPLE 3: Issued against pattern
            ("A challan HR67070221005165119 issued against HR51BM6192. The total challan amount is 500. For more details visit: https://bit.ly/2UZK16l. Thanks, Faridabad Traffic Police.", {
                "challan_number": "HR67070221005165119",
                "vehicle_number": "HR51BM6192",
                "fine_amount": "500",
                "payment_link": "https://bit.ly/2UZK16l",
                "traffic_authority": "Faridabad Traffic Police",
                "challan_status": "issued"
            }, "challan"),
            
            # MISSING EXAMPLE 4: Another issued against pattern
            ("A challan GJ4160807230909053094 issued against GJ05RK8881. The total challan amount is 500. For more details visit: https://bit.ly/2UZK16l. Thanks, Surat City Traffic Police.", {
                "challan_number": "GJ4160807230909053094",
                "vehicle_number": "GJ05RK8881",
                "fine_amount": "500",
                "payment_link": "https://bit.ly/2UZK16l",
                "traffic_authority": "Surat City Traffic Police",
                "challan_status": "issued"
            }, "challan"),
            
            # Original working examples (should still work)
            ("Your traffic challan bearing No. DL116709240411110024 For vehicle no. HR87K5231is sent to virtual court for disposal as per law. You will shortly receive a message/update from virtual court on your registered number enabling you to make the payment on online web portal. Delhi Traffic Police", {
                "challan_number": "DL116709240411110024",
                "vehicle_number": "HR87K5231",
                "traffic_authority": "Delhi Traffic Police",
                "challan_status": "issued"
            }, "challan"),
            
            ("Payment of Rs. 100.00 for MPTURN150520240010822 has been received, kindly logon to https://mptreasury.gov.in/MPCTP/portal.htm?viewName=printChallan&registered=N for challan receipt using challan search.-Rgrds MPTreasury", {
                "challan_number": "MPTURN150520240010822",
                "fine_amount": "100.00",
                "payment_link": "https://mptreasury.gov.in/MPCTP/portal.htm?viewName=printChallan&registered=N",
                "traffic_authority": "MP Treasury",
                "challan_status": "paid"
            }, "challan"),
            
            # False Challan Messages (Should be REJECTED)
            ("Your vehicle insurance is expiring soon. Renew now to avoid penalties.", None, "challan"),
        ]
        
        all_test_cases = [("OTP", otp_test_cases), ("EMI", emi_test_cases), ("CHALLAN", challan_test_cases)]
        total_correct = 0
        total_tests = 0
        
        for test_type, test_cases in all_test_cases:
            print(f"\n--- {test_type} Test Cases ---")
            correct_count = 0
            
            for i, test_case in enumerate(test_cases):
                if test_type == "OTP":
                    message, expected_otp, msg_type = test_case
                    result = self.parse_single_message(message, "", msg_type)
                    is_correct = False
                    if result['status'] == 'parsed' and result.get('otp_code') == expected_otp:
                        is_correct = True
                    elif result['status'] == 'rejected' and expected_otp is None:
                        is_correct = True
                elif test_type in ["EMI", "CHALLAN"]:
                    message, expected_data, msg_type = test_case
                    result = self.parse_single_message(message, "", msg_type)
                    is_correct = False
                    if expected_data is None:
                        is_correct = (result['status'] == 'rejected')
                    else:
                        if result['status'] == 'parsed':
                            # Check if key fields match expectations
                            is_correct = True
                            for key, expected_value in expected_data.items():
                                if result.get(key) != expected_value:
                                    is_correct = False
                                    print(f"    MISMATCH: {key} = '{result.get(key)}' (expected '{expected_value}')")
                                    break
                
                if is_correct:
                    correct_count += 1
                    status = "PASS"
                else:
                    status = "FAIL"
                
                print(f"\nTest {i+1}: {status}")
                print(f"  Message: '{message[:80]}{'...' if len(message) > 80 else ''}'")
                print(f"  Result: {result.get('status')}, Score: {result.get('confidence_score')}%")
                
                if test_type == "OTP" and result['status'] == 'parsed':
                    print(f"  OTP: {result.get('otp_code')}")
                elif test_type == "EMI" and result['status'] == 'parsed':
                    print(f"  Amount: Rs.{result.get('emi_amount')}, Bank: {result.get('bank_name')}")
                elif test_type == "CHALLAN" and result['status'] == 'parsed':
                    print(f"  Challan: {result.get('challan_number')}, Vehicle: {result.get('vehicle_number')}")
                    print(f"  Fine: Rs.{result.get('fine_amount')}, Authority: {result.get('traffic_authority')}")
                    print(f"  Status: {result.get('challan_status')}, Link: {result.get('payment_link') and 'Yes' or 'No'}")
                elif not is_correct:
                    print(f"  Reason: {result.get('reason', 'Failed validation')}")
            
            total_correct += correct_count
            total_tests += len(test_cases)
            print(f"\n{test_type} Tests: {correct_count}/{len(test_cases)} passed")
        
        print(f"\n--- Overall Test Results: {total_correct}/{total_tests} Passed ---")
        if total_correct == total_tests:
            print("ALL TESTS PASSED! Enhanced patterns working correctly.")
        else:
            print(f"ATTENTION: {total_tests - total_correct} test(s) failed. Check patterns.")

    def interactive_message_analyzer(self):
        """Interactive analyzer for OTP, EMI, and challan messages - Enhanced"""
        print("\nInteractive Message Analyzer v8.0 (OTP, EMI & Traffic Challan)")
        print("=" * 60)
        print("Enhanced with missing pattern detection for Maharashtra Police, Sama.live, etc.")
        print("Enter messages to analyze (type 'quit' to exit)")
        
        while True:
            print("\n" + "-" * 60)
            message = input("Enter message: ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                break
            
            if not message:
                continue
            
            sender = input("Enter sender name (optional): ").strip()
            
            message_type = input("Message type (otp/emi/challan/auto) [auto]: ").strip().lower()
            if not message_type:
                message_type = "auto"
            
            print("\nDetailed Analysis:")
            print("-" * 40)
            
            result = self.parse_single_message(message, sender, message_type)
            
            print(f"Message Type: {result.get('message_type', 'Unknown')}")
            print(f"Confidence Score: {result['confidence_score']}%")
            print(f"Final Status: {result['status']}")
            
            if result['status'] == 'parsed':
                if result['message_type'] == 'otp':
                    print(f"OTP Code: {result.get('otp_code')}")
                    print(f"Company: {result.get('company_name')}")
                elif result['message_type'] == 'emi':
                    print(f"EMI Amount: Rs.{result.get('emi_amount')}")
                    print(f"Due Date: {result.get('emi_due_date')}")
                    print(f"Bank: {result.get('bank_name')}")
                    print(f"Account: {result.get('account_number')}")
                elif result['message_type'] == 'challan':
                    print(f"Challan Number: {result.get('challan_number')}")
                    print(f"Vehicle Number: {result.get('vehicle_number')}")
                    print(f"Fine Amount: Rs.{result.get('fine_amount')}")
                    print(f"Payment Link: {result.get('payment_link')}")
                    print(f"Authority: {result.get('traffic_authority')}")
                    print(f"Status: {result.get('challan_status')}")
                    
                    # Enhanced status explanation
                    status = result.get('challan_status')
                    if status == 'paid':
                        print("  -> This is a payment confirmation/receipt")
                    elif status == 'pending':
                        print("  -> This challan requires payment")
                    elif status == 'issued':
                        print("  -> This is a new challan notification")
            else:
                print(f"Rejection Reason: {result.get('reason')}")


def main():
    parser = EnhancedMessageParser()
    
    print("Enhanced Message Parser v8.0 - OTP, EMI, and Traffic Challan Classification")
    print("With MISSING PATTERN Detection for Maharashtra Police, Sama.live, Short Challans")
    print("=" * 80)
    
    while True:
        print("\nChoose an option:")
        print("1. Test parser with sample messages (including MISSING examples)")
        print("2. Interactive message analysis")
        print("3. Process CSV file")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            parser.test_enhanced_parser()
        elif choice == '2':
            parser.interactive_message_analyzer()
        elif choice == '3':
            input_file = input("Enter the path to your CSV file: ").strip().strip('"')
            if not input_file:
                print("No file path provided.")
                continue
            
            message_type = input("Message type to parse (otp/emi/challan/auto) [auto]: ").strip().lower()
            if not message_type:
                message_type = "auto"
            
            output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
            if not output_file:
                output_file = None
            
            results = parser.process_csv_file(input_file, output_file, message_type)
            
            if results:
                print(f"\nProcessing completed successfully!")
                print(f"Enhanced detection now includes:")
                print("  • Maharashtra Police + Online Lok Adalat")
                print("  • Sama.live platform integration")
                print("  • Short numeric challan numbers (8+ digits)")
                print("  • 'Issued against' vehicle patterns")
                print("  • Enhanced fine amount detection")
                print("  • Multi-state traffic authority recognition")
            else:
                print("Processing failed. Please check your file path and format.")
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()