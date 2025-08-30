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
        
        # Company patterns
        self.compiled_company_patterns = {}
        for company, patterns in self.company_patterns.items():
            self.compiled_company_patterns[company] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self.compiled_bank_patterns = {}
        for bank, patterns in self.bank_patterns.items():
            self.compiled_bank_patterns[bank] = [re.compile(p, re.IGNORECASE) for p in patterns]

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

    # --- NEW EMI PARSING METHODS ---
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
        """Parse a single message for either OTP or EMI content"""
        clean_message = self.clean_text(message)
        
        if message_type == "auto":
            # Auto-detect message type
            if self.is_emi_message(clean_message):
                return self.parse_emi_message(message, sender_name)
            else:
                return self.parse_otp_message(message, sender_name)
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
        """Process CSV file for both OTP and EMI messages"""
        print("Enhanced Message Parser - Analyzing Messages for OTP and EMI Content")
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
        
        # Separate OTP and EMI messages
        otp_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'otp']
        emi_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'emi']
        
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'total_parsed_messages': len(parsed_messages),
                'otp_messages_found': len(otp_messages),
                'emi_messages_found': len(emi_messages),
                'rejected_messages': len(rejected_messages),
                'detection_rate': round((len(parsed_messages) / total_messages) * 100, 2),
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '5.0_otp_emi_combined'
            },
            'summary_statistics': {
                'otp_stats': self.generate_otp_summary_stats(otp_messages),
                'emi_stats': self.generate_emi_summary_stats(emi_messages)
            },
            'otp_messages': otp_messages,
            'emi_messages': emi_messages,
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

    def display_parsing_summary(self, results: Dict):
        """Display comprehensive parsing summary for both OTP and EMI"""
        metadata = results['metadata']
        otp_stats = results.get('summary_statistics', {}).get('otp_stats', {})
        emi_stats = results.get('summary_statistics', {}).get('emi_stats', {})
        
        print("\n" + "="*80)
        print("ENHANCED MESSAGE PARSING RESULTS SUMMARY")
        print("="*80)
        
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"Total Parsed Messages: {metadata['total_parsed_messages']:,}")
        print(f"  - OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"  - EMI Messages Found: {metadata['emi_messages_found']:,}")
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
            print(f"  High Confidence (≥80): {quality_metrics.get('high_confidence_messages', 0)}")
        
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
                print(f"  Average EMI: ₹{amount_stats.get('average_amount', 0):,.2f}")
                print(f"  Total EMI Value: ₹{amount_stats.get('total_emi_value', 0):,.2f}")
            
            print(f"\nEMI Data Completeness:")
            print(f"  Messages with Amount: {quality_metrics.get('messages_with_amount', 0)}/{emi_stats['total_count']}")
            print(f"  Messages with Bank: {quality_metrics.get('messages_with_bank', 0)}/{emi_stats['total_count']}")
            print(f"  Messages with Account#: {quality_metrics.get('messages_with_account', 0)}/{emi_stats['total_count']}")
            print(f"  Messages with Due Date: {quality_metrics.get('messages_with_due_date', 0)}/{emi_stats['total_count']}")

    def test_enhanced_parser(self):
        """Comprehensive test suite for both OTP and EMI parsing"""
        print("--- Running Enhanced Parser Test Suite ---")
        
        # OTP Test Cases
        otp_test_cases = [
            # False Positives (Should be REJECTED)
            ("Thank you for your order #567890 from Zomato.", None, "otp"),
            ("Flash Sale! Get 50% off on orders above Rs. 1500. Use code SAVE50.", None, "otp"),
            ("Your account balance is INR 12,345.67 as of 29-Aug-2025.", None, "otp"),
            # True Positives (Should be PARSED)
            ("OTP for Aarogya Setu is 1357. Stay safe.", "1357", "otp"),
            ("Your Discord verification code is 887766", "887766", "otp"),
            ("Your Signal registration code is 246-810.", "246810", "otp"),
            ("123 456 is your Instagram login code. Don't share it.", "123456", "otp"),
        ]
        
        # EMI Test Cases
        emi_test_cases = [
            # True EMI Messages (Should be PARSED)
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
            ("Loan EMI Amount is: 1500, Last EMI Payment received for: 20/12/2021", {
                "emi_amount": "1500",
                "emi_due_date": "20/12/2021"
            }, "emi"),
            # False EMI Messages (Should be REJECTED)
            ("Get easy EMI options starting from just Rs 999! Shop now with 0% interest!", None, "emi"),
            ("Avail no cost EMI facility on purchases above Rs 5000. Limited time offer!", None, "emi"),
        ]
        
        all_test_cases = [("OTP", otp_test_cases), ("EMI", emi_test_cases)]
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
                else:  # EMI
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
                                    break
                
                if is_correct:
                    correct_count += 1
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                print(f"\nTest {i+1}: {status}")
                print(f"  Message: '{message[:60]}{'...' if len(message) > 60 else ''}'")
                print(f"  Result: {result.get('status')}, Score: {result.get('confidence_score')}%")
                
                if test_type == "OTP" and result['status'] == 'parsed':
                    print(f"  OTP: {result.get('otp_code')}")
                elif test_type == "EMI" and result['status'] == 'parsed':
                    print(f"  Amount: ₹{result.get('emi_amount')}, Bank: {result.get('bank_name')}")
            
            total_correct += correct_count
            total_tests += len(test_cases)
            print(f"\n{test_type} Tests: {correct_count}/{len(test_cases)} passed")
        
        print(f"\n--- Overall Test Results: {total_correct}/{total_tests} Passed ---")

    def interactive_message_analyzer(self):
        """Interactive analyzer for both OTP and EMI messages"""
        print("\nInteractive Message Analyzer (OTP & EMI)")
        print("=" * 60)
        print("Enter messages to analyze (type 'quit' to exit)")
        
        while True:
            print("\n" + "-" * 60)
            message = input("Enter message: ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                break
            
            if not message:
                continue
            
            sender = input("Enter sender name (optional): ").strip()
            
            message_type = input("Message type (otp/emi/auto) [auto]: ").strip().lower()
            if not message_type:
                message_type = "auto"
            
            print("\nDetailed Analysis:")
            print("-" * 40)
            
            result = self.parse_single_message(message, sender, message_type)
            
            print(f"Message Type: {result.get('message_type', 'Unknown')}")
            print(f"Confidence Score: {result['confidence_score']}")
            print(f"Final Status: {result['status']}")
            
            if result['status'] == 'parsed':
                if result['message_type'] == 'otp':
                    print(f"OTP Code: {result.get('otp_code')}")
                    print(f"Company: {result.get('company_name')}")
                elif result['message_type'] == 'emi':
                    print(f"EMI Amount: ₹{result.get('emi_amount')}")
                    print(f"Due Date: {result.get('emi_due_date')}")
                    print(f"Bank: {result.get('bank_name')}")
                    print(f"Account: {result.get('account_number')}")
            else:
                print(f"Rejection Reason: {result.get('reason')}")


def main():
    parser = EnhancedMessageParser()
    
    print("Enhanced Message Parser with OTP and EMI Classification")
    print("=" * 80)
    
    while True:
        print("\nChoose an option:")
        print("1. Test parser with sample messages")
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
            
            message_type = input("Message type to parse (otp/emi/auto) [auto]: ").strip().lower()
            if not message_type:
                message_type = "auto"
            
            output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
            if not output_file:
                output_file = None
            
            results = parser.process_csv_file(input_file, output_file, message_type)
            
            if results:
                print(f"\nProcessing completed successfully!")
            else:
                print("Processing failed. Please check your file path and format.")
        elif choice == '4':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()





























# import pandas as pd
# import re
# import json
# from typing import Dict, List, Optional, Tuple
# import time
# from difflib import SequenceMatcher

# class EnhancedOTPMessageParser:
#     def __init__(self):
#         # --- Robust OTP Extraction Patterns (Updated for Alphanumeric and More Formats) ---
#         self.otp_patterns = [
#             # --- NEW: Alphanumeric and More Specific Patterns (Placed at the top for priority) ---
#             r'\b([A-Z0-9]{6,8})\s*is\s*your\s*(?:one\s*time\s*password|otp|code|pin)\b', # e.g., "1G24X3 is your OTP"
#             r'(?:otp|code|pin|password)\s*is\s*[:\s]*\b([A-Z0-9]{4,8})\b',             # e.g., "Your OTP is: ABC123D"
#             r'Your\s*(?:\w+\s*)?(?:code|otp|pin)\s*:\s*\b(\d{4,8})\b',                # e.g., "Your Facebook code: 123456"
#             r'verification\s*(?:code|pin)\s*is\s*\b(\d{4,8})\b',                    # e.g., "verification pin is 5678"
#             r'\b[gG]-(\d{6})\b',                                                    # Google's G-XXXXXX format

#             # --- EXISTING: Refined and Kept for Broad Coverage ---
#             r'(?:otp|code|password)\s*is\s*[:\s]*(\d{3}[- ]?\d{3})\b', # Handles "123 456" or "123-456" formats
#             r'\b(\d{3}[- ]?\d{3})\s*is\s*your\s*(?:instagram|signal|discord)?\s*(?:login|verification|registration)?\s*code',
#             r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code|pin)\b', # Added 'pin'
#             r'enter\s*(\d{4,8})\s*to',

#             # --- A slightly broader but common pattern, kept lower in priority ---
#             r'(?:otp|code|password|is|:)\s*\b(\d{4,8})\b',
#         ]

#         # --- General Keywords & Patterns for Confidence Scoring ---
#         self.true_otp_patterns = [
#             r'\b(otp|one[- ]?time[- ]?password|verification code|login code|registration code|pin)\b', # Added pin
#             r'\b(enter\s*[\d-]+)\b',
#             r'(\w{4,8})\s*is\s*your', # Now alphanumeric
#             r'valid\s*for\s*\d+\s*minutes'
#         ]
        
#         # --- Company & Service Keywords ---
#         self.company_patterns = {
#             'Google': [r'\bgoogle\b'], 'Google Pay': [r'\bgoogle pay\b'],
#             'Axis Bank': [r'\baxis bank\b'], 'Instagram': [r'\binstagram\b'],
#             'Discord': [r'\bdiscord\b'], 'Signal': [r'\bsignal\b'],
#             'Aarogya Setu': [r'aarogya setu'],
#             'Amazon': [r'\bamazon\b'], 'Flipkart': [r'\bflipkart\b'],
#             'Paytm': [r'\bpaytm\b'], 'Swiggy': [r'\bswiggy\b'],
#             'HDFC': [r'\bhdfc\b'], 'SBI': [r'\bsbi\b'], 'ICICI': [r'\bicici\b'],
#             'UTS Mobile Ticket': [r'\buts\s*mobile\s*ticket\b', r'\buts\b'],
#             'CRIS': [r'\bcris\b'], 'Dream11': [r'\bdream11\b'], 'Zupee': [r'\bzupee\b'],
#             'Meesho': [r'\bmeesho\b'], 'AJIO': [r'\bajio\b'], 'Myntra': [r'\bmyntra\b'],
#             'Zomato': [r'\bzomato\b'], 'Ola': [r'\bola\b'], 'Uber': [r'\buber\b'],
#             'Jio': [r'\bjio\b'], 'Airtel': [r'\bairtel\b'], 'Vi': [r'\bvi\b'],
#             'WhatsApp': [r'\bwhatsapp\b'], 'Facebook': [r'\bfacebook\b'],
#         }

#         # --- STRONG EXCLUSION PATTERNS ---
#         self.strong_exclusion_patterns = [
#             r'order\s*#\s*\w+',              # For "order #567890" or "order #ABC123"
#             r'order\s*(?:number|no|id)\s*[:\s]*\w+', # For "order number", "order no", etc.
#             r'use\s*code\s*[A-Z]{4,}\d*',       # For "Use code SAVE50", avoid matching OTPs like "1G24X3"
#             r'account\s*balance',           # For "Your account balance is..."
#             r'bal\s*:\s*rs',                # For "bal: rs..."
#             r'tracking\s*number',           # For "tracking number"
#             r'flight\s*number',             # For "flight number"
#             r'call\s*us\s*at',              # For phone numbers
#             r'promo\s*code',                # For "promo code"
#         ]

#         # --- Expiry/validity patterns (IMPROVED) ---
#         self.expiry_patterns = [
#             r'\bvalid\s*(?:for|till|upto)\s*(?:the\s*)?(?:next\s*)?(\d+)\s*(minutes?|mins?|min|hours?|hrs?|hr|seconds?|secs?|sec)\b',
#             r'\bexpires?\s*(?:in|within|after)\s*(\d+)\s*(minutes?|mins?|min|hours?|hrs?|hr|seconds?|secs?|sec)\b',
#         ]

#         # --- Purpose/Action patterns ---
#         self.purpose_patterns = {
#             'Login': [r'\bto\s*(?:login|log\s*in|sign\s*in)\b', r'\bfor\s*(?:login|log\s*in|sign\s*in)\b'],
#             'Verification': [r'\bto\s*(?:verify|verification)\b', r'\bfor\s*(?:verification|account\s*verification)\b'],
#             'Transaction': [r'\bto\s*(?:complete|authorize)\s*(?:transaction|payment)\b'],
#             'Payment': [r'for\s*payment'],
#         }

#         # --- Security warning patterns ---
#         self.security_patterns = [
#             r'\bdo\s*not\s*share\b',
#             r'\bnever\s*share\b', 
#         ]

#         # --- Compile all patterns for performance ---
#         self.compiled_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.otp_patterns]
#         self.compiled_true_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.true_otp_patterns]
#         self.compiled_strong_exclusions = [re.compile(p, re.IGNORECASE) for p in self.strong_exclusion_patterns]
#         self.compiled_expiry_patterns = [re.compile(p, re.IGNORECASE) for p in self.expiry_patterns]
#         self.compiled_security_patterns = [re.compile(p, re.IGNORECASE) for p in self.security_patterns]
        
#         self.compiled_company_patterns = {}
#         for company, patterns in self.company_patterns.items():
#             self.compiled_company_patterns[company] = [re.compile(p, re.IGNORECASE) for p in patterns]

#         self.compiled_purpose_patterns = {}
#         for purpose, patterns in self.purpose_patterns.items():
#             self.compiled_purpose_patterns[purpose] = [re.compile(p, re.IGNORECASE) for p in patterns]

#     def clean_text(self, text: str) -> str:
#         if pd.isna(text): return ""
#         return str(text).strip()
        
#     def extract_otp_code(self, text: str) -> Optional[str]:
#         for pattern in self.compiled_otp_patterns:
#             match = pattern.search(text)
#             if match:
#                 otp = match.group(1)
#                 return re.sub(r'[- ]', '', otp)
        
#         if any(p.search(text.lower()) for p in self.compiled_true_otp_patterns):
#             potential_otps = re.findall(r'\b\d{4,8}\b', text)
#             if potential_otps:
#                 return potential_otps[0]
#             potential_alpha_otps = re.findall(r'\b[A-Z0-9]{4,8}\b', text)
#             if potential_alpha_otps:
#                  return potential_alpha_otps[0]

#         return None

#     def extract_company_name(self, text: str, sender_name: str = "") -> Optional[str]:
#         combined_text = f"{text.lower()} {sender_name.lower()}"
#         for company, patterns in self.compiled_company_patterns.items():
#             if any(p.search(combined_text) for p in patterns):
#                 return company
#         return None

#     def calculate_otp_confidence_score(self, text: str) -> int:
#         score = 0
#         text_lower = text.lower()
        
#         if any(p.search(text_lower) for p in self.compiled_strong_exclusions):
#             return 0

#         otp_code = self.extract_otp_code(text)

#         if otp_code:
#             score += 50
        
#         if any(p.search(text_lower) for p in self.compiled_true_otp_patterns):
#             score += 25
        
#         if self.extract_company_name(text_lower):
#             score += 15
        
#         if "don't share" in text_lower or "do not share" in text_lower or "valid for" in text_lower:
#             score += 10

#         return max(0, min(100, score))

#     def extract_purpose(self, text: str) -> Optional[str]:
#         text_lower = text.lower()
#         for purpose, patterns in self.compiled_purpose_patterns.items():
#             if any(p.search(text_lower) for p in patterns):
#                 return purpose
#         return None
        
#     def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
#         for pattern in self.compiled_expiry_patterns:
#             match = pattern.search(text)
#             if match:
#                 unit = match.group(2).lower()
#                 if unit.startswith('min'):
#                     normalized_unit = 'minute'
#                 elif unit.startswith('sec'):
#                     normalized_unit = 'second'
#                 elif unit.startswith('hr'):
#                     normalized_unit = 'hour'
#                 else:
#                     normalized_unit = unit.rstrip('s')

#                 return {
#                     'duration': match.group(1),
#                     'unit': normalized_unit,
#                     'full_text': match.group(0)
#                 }
#         return None

#     def extract_security_warnings(self, text: str) -> List[str]:
#         warnings = []
#         for pattern in self.compiled_security_patterns:
#             match = pattern.search(text)
#             if match:
#                 warnings.append(match.group(0))
#         return warnings

#     def parse_single_message(self, message: str, sender_name: str = "") -> Dict:
#         clean_message = self.clean_text(message)
#         combined_text = f"{clean_message} {sender_name}"
        
#         confidence_score = self.calculate_otp_confidence_score(combined_text)
        
#         if confidence_score >= 50:
#             otp_code = self.extract_otp_code(clean_message)
#             if otp_code:
#                 result = {
#                     'status': 'parsed',
#                     'confidence_score': confidence_score,
#                     'otp_code': otp_code,
#                     'company_name': self.extract_company_name(clean_message, sender_name),
#                     'purpose': self.extract_purpose(clean_message),
#                     'expiry_info': self.extract_expiry_time(clean_message),
#                     'security_warnings': self.extract_security_warnings(clean_message),
#                     'raw_message': message,
#                 }
#                 return result

#         return {
#             'status': 'rejected',
#             'reason': 'Message did not meet the confidence threshold for an OTP.',
#             'confidence_score': confidence_score,
#             'message_preview': clean_message[:100],
#         }

#     def process_csv_file(self, input_file: str, output_file: str = None) -> Dict:
#         print("Enhanced OTP Message Parser - Analyzing Messages for OTP Content")
#         print("=" * 80)
#         print("Loading CSV file...")
#         start_time = time.time()
        
#         try:
#             df = pd.read_csv(input_file, dtype=str)
#         except Exception as e:
#             print(f"Error reading CSV: {e}")
#             return None
        
#         print(f"Loaded {len(df):,} rows in {time.time() - start_time:.2f} seconds")
        
#         if 'message' not in df.columns:
#             print("Error: 'message' column not found")
#             return None
        
#         if 'sender_name' not in df.columns:
#             print("Warning: 'sender_name' column not found. Using empty values.")
#             df['sender_name'] = ""
        
#         print(f"Analyzing {len(df):,} messages for OTP content...")
        
#         otp_messages = []
#         rejected_messages = []
        
#         print("Starting message analysis...")
#         parse_start = time.time()
        
#         batch_size = 1000
#         total_messages = len(df)
        
#         for i in range(0, total_messages, batch_size):
#             end_idx = min(i + batch_size, total_messages)
            
#             for idx in range(i, end_idx):
#                 row = df.iloc[idx]
#                 message = row['message'] if pd.notna(row['message']) else ""
#                 sender = row['sender_name'] if pd.notna(row['sender_name']) else ""
                
#                 parsed_result = self.parse_single_message(message, sender)
#                 parsed_result['original_index'] = idx
                
#                 if parsed_result['status'] == 'parsed':
#                     otp_messages.append(parsed_result)
#                 else:
#                     rejected_messages.append(parsed_result)
            
#             progress = (end_idx / total_messages) * 100
#             elapsed = time.time() - parse_start
#             rate = end_idx / elapsed if elapsed > 0 else 0
            
#             if (end_idx % 10000 == 0) or (end_idx == total_messages):
#                 print(f"Progress: {progress:.1f}% ({end_idx:,}/{total_messages:,}) | "
#                       f"Rate: {rate:.0f} msgs/sec | "
#                       f"OTP Found: {len(otp_messages):,} | "
#                       f"Rejected: {len(rejected_messages):,}")
        
#         parse_time = time.time() - parse_start
#         print(f"\nAnalysis completed in {parse_time/60:.1f} minutes")
        
#         results = {
#             'metadata': {
#                 'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
#                 'total_input_messages': int(total_messages),
#                 'otp_messages_found': len(otp_messages),
#                 'rejected_messages': len(rejected_messages),
#                 'otp_detection_rate': round((len(otp_messages) / total_messages) * 100, 2) if total_messages > 0 else 0,
#                 'processing_time_minutes': round(parse_time / 60, 2),
#                 'parser_version': '5.0_alphanumeric_support'
#             },
#             'summary_statistics': self.generate_summary_stats(otp_messages),
#             'otp_messages': otp_messages,
#             'sample_rejected_messages': rejected_messages[:10]
#         }
        
#         self.display_parsing_summary(results)
        
#         if output_file is None:
#             base_name = input_file.replace('.csv', '')
#             output_file = f"{base_name}_otp_parsed.json"
        
#         print(f"\nSaving results to: {output_file}")
        
#         try:
#             with open(output_file, 'w', encoding='utf-8') as f:
#                 json.dump(results, f, indent=2, ensure_ascii=False)
#             print("Results saved successfully!")
#         except Exception as e:
#             print(f"Error saving results: {e}")
#             return None
        
#         return results

#     def generate_summary_stats(self, otp_messages: List[Dict]) -> Dict:
#         if not otp_messages:
#             return {}
        
#         total_otp = len(otp_messages)
        
#         companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
#         company_counts = {}
#         for company in companies:
#             company_counts[company] = company_counts.get(company, 0) + 1
        
#         purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
#         purpose_counts = {}
#         for purpose in purposes:
#             purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        
#         confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
#         avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
#         return {
#             'distributions': {
#                 'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
#                 'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
#             },
#             'quality_metrics': {
#                 'average_confidence_score': round(avg_confidence, 2),
#                 'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
#                 'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
#                 'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
#             }
#         }

#     def display_parsing_summary(self, results: Dict):
#         metadata = results['metadata']
#         stats = results.get('summary_statistics', {})
        
#         print("\n" + "="*80)
#         print("OTP PARSING RESULTS SUMMARY")
#         print("="*80)
        
#         print(f"Total Input Messages: {metadata['total_input_messages']:,}")
#         print(f"OTP Messages Found: {metadata['otp_messages_found']:,}")
#         print(f"Messages Rejected: {metadata['rejected_messages']:,}")
#         print(f"OTP Detection Rate: {metadata['otp_detection_rate']}%")
        
#         if not stats:
#             print("\nNo OTP messages found to analyze.")
#             return
        
#         distributions = stats.get('distributions', {})
#         quality_metrics = stats.get('quality_metrics', {})
        
#         print("\n" + "="*60)
#         print("TOP COMPANIES/SERVICES")
#         print("="*60)
        
#         if distributions.get('top_companies'):
#             for company, count in list(distributions.get('top_companies', {}).items())[:10]:
#                 percentage = (count / metadata['otp_messages_found']) * 100
#                 print(f"{company}: {count:,} ({percentage:.1f}%)")
#         else:
#             print("No companies identified.")
        
#         print("\n" + "="*60)
#         print("QUALITY METRICS")
#         print("="*60)
        
#         print(f"Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")

#     def test_enhanced_parser(self):
#         """A comprehensive test suite to validate parser accuracy."""
#         test_cases = [
#             # --- NEW: Test cases for updated patterns ---
#             ("1G24X3 is your OTP. Please do not share this code with anyone else. WMSSPL", "1G24X3"), # Alphanumeric
#             ("Your Swiggy code: 5678. It will expire in 10 minutes.", "5678"), # "code:" format
#             ("Your verification pin is 990011 for transaction.", "990011"), # "pin is" format
#             ("Your one time password is: AB34CD56", "AB34CD56"), # Alphanumeric with "is:"

#             # --- Existing False Positives (Should be REJECTED) ---
#             ("Thank you for your order #567890 from Zomato.", None),
#             ("Flash Sale! Get 50% off on orders above Rs. 1500. Use code SAVE50.", None),
#             ("Your account balance is INR 12,345.67 as of 29-Aug-2025.", None),

#             # --- Existing True Positives (Should be PARSED) ---
#             ("OTP for Aarogya Setu is 1357. Stay safe.", "1357"),
#             ("Your Discord verification code is 887766", "887766"),
#             ("Your Signal registration code is 246-810.", "246810"),
#             ("123 456 is your Instagram login code. Don't share it.", "123456"),
#         ]

#         print("--- Running High-Precision Parser Test Suite ---")
#         correct_count = 0
#         for i, (message, expected_otp) in enumerate(test_cases):
#             result = self.parse_single_message(message)
#             is_correct = False
#             if result['status'] == 'parsed' and result['otp_code'] == expected_otp:
#                 is_correct = True
#             elif result['status'] == 'rejected' and expected_otp is None:
#                 is_correct = True
            
#             if is_correct:
#                 correct_count += 1
#                 status = "✅ PASS"
#             else:
#                 status = "❌ FAIL"
            
#             print(f"\nTest {i+1}: {status}")
#             print(f"  Message: '{message}'")
#             print(f"  Result: {result.get('status')}, OTP: {result.get('otp_code')}, Score: {result.get('confidence_score')}")
            
#         print(f"\n--- Test Complete: {correct_count}/{len(test_cases)} Passed ---")

#     def interactive_message_analyzer(self):
#         print("\nInteractive OTP Message Analyzer")
#         print("=" * 50)
#         print("Enter messages to analyze (type 'quit' to exit)")
        
#         while True:
#             print("\n" + "-" * 50)
#             message = input("Enter message: ").strip()
            
#             if message.lower() in ['quit', 'exit', 'q']:
#                 break
            
#             if not message:
#                 continue
            
#             sender = input("Enter sender name (optional): ").strip()
            
#             print("\nDetailed Analysis:")
#             print("-" * 30)
            
#             result = self.parse_single_message(message, sender)
            
#             print(f"Confidence Score: {result['confidence_score']}")
#             print(f"Final Status: {result['status']}")
            
#             if result['status'] == 'parsed':
#                 print(f"OTP Code: {result.get('otp_code')}")
#                 print(f"Company: {result.get('company_name')}")
#             else:
#                 print(f"Rejection Reason: {result.get('reason')}")

# def main():
#     parser = EnhancedOTPMessageParser()
    
#     print("Enhanced OTP Message Parser with Smart Classification")
#     print("=" * 80)
    
#     test_parser = input("\nWould you like to test the parser with sample messages? (y/n): ").lower().strip()
#     if test_parser == 'y':
#         parser.test_enhanced_parser()
    
#     interactive_test = input("\nWould you like to test individual messages interactively? (y/n): ").lower().strip()
#     if interactive_test == 'y':
#         parser.interactive_message_analyzer()
    
#     process_csv = input(f"\nWould you like to process a CSV file? (y/n): ").lower().strip()
#     if process_csv == 'y':
#         input_file = input("Enter the path to your CSV file: ").strip().strip('"')
#         if not input_file:
#             print("No file path provided. Exiting.")
#             return
        
#         output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
#         if not output_file:
#             output_file = None
        
#         results = parser.process_csv_file(input_file, output_file)
        
#         if results:
#             print(f"\nProcessing completed successfully!")
#         else:
#             print("Processing failed. Please check your file path and format.")

# if __name__ == "__main__":
#     main()