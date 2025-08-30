import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import time
from difflib import SequenceMatcher

class EnhancedOTPMessageParser:
    def __init__(self):
        # --- Robust OTP Extraction Patterns (Updated for Alphanumeric and More Formats) ---
        self.otp_patterns = [
            # --- NEW: Alphanumeric and More Specific Patterns (Placed at the top for priority) ---
            r'\b([A-Z0-9]{6,8})\s*is\s*your\s*(?:one\s*time\s*password|otp|code|pin)\b', # e.g., "1G24X3 is your OTP"
            r'(?:otp|code|pin|password)\s*is\s*[:\s]*\b([A-Z0-9]{4,8})\b',             # e.g., "Your OTP is: ABC123D"
            r'Your\s*(?:\w+\s*)?(?:code|otp|pin)\s*:\s*\b(\d{4,8})\b',                # e.g., "Your Facebook code: 123456"
            r'verification\s*(?:code|pin)\s*is\s*\b(\d{4,8})\b',                    # e.g., "verification pin is 5678"
            r'\b[gG]-(\d{6})\b',                                                    # Google's G-XXXXXX format

            # --- EXISTING: Refined and Kept for Broad Coverage ---
            r'(?:otp|code|password)\s*is\s*[:\s]*(\d{3}[- ]?\d{3})\b', # Handles "123 456" or "123-456" formats
            r'\b(\d{3}[- ]?\d{3})\s*is\s*your\s*(?:instagram|signal|discord)?\s*(?:login|verification|registration)?\s*code',
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code|pin)\b', # Added 'pin'
            r'enter\s*(\d{4,8})\s*to',

            # --- A slightly broader but common pattern, kept lower in priority ---
            r'(?:otp|code|password|is|:)\s*\b(\d{4,8})\b',
        ]

        # --- General Keywords & Patterns for Confidence Scoring ---
        self.true_otp_patterns = [
            r'\b(otp|one[- ]?time[- ]?password|verification code|login code|registration code|pin)\b', # Added pin
            r'\b(enter\s*[\d-]+)\b',
            r'(\w{4,8})\s*is\s*your', # Now alphanumeric
            r'valid\s*for\s*\d+\s*minutes'
        ]
        
        # --- Company & Service Keywords ---
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

        # --- STRONG EXCLUSION PATTERNS ---
        self.strong_exclusion_patterns = [
            r'order\s*#\s*\w+',              # For "order #567890" or "order #ABC123"
            r'order\s*(?:number|no|id)\s*[:\s]*\w+', # For "order number", "order no", etc.
            r'use\s*code\s*[A-Z]{4,}\d*',       # For "Use code SAVE50", avoid matching OTPs like "1G24X3"
            r'account\s*balance',           # For "Your account balance is..."
            r'bal\s*:\s*rs',                # For "bal: rs..."
            r'tracking\s*number',           # For "tracking number"
            r'flight\s*number',             # For "flight number"
            r'call\s*us\s*at',              # For phone numbers
            r'promo\s*code',                # For "promo code"
        ]

        # --- Expiry/validity patterns (IMPROVED) ---
        self.expiry_patterns = [
            r'\bvalid\s*(?:for|till|upto)\s*(?:the\s*)?(?:next\s*)?(\d+)\s*(minutes?|mins?|min|hours?|hrs?|hr|seconds?|secs?|sec)\b',
            r'\bexpires?\s*(?:in|within|after)\s*(\d+)\s*(minutes?|mins?|min|hours?|hrs?|hr|seconds?|secs?|sec)\b',
        ]

        # --- Purpose/Action patterns ---
        self.purpose_patterns = {
            'Login': [r'\bto\s*(?:login|log\s*in|sign\s*in)\b', r'\bfor\s*(?:login|log\s*in|sign\s*in)\b'],
            'Verification': [r'\bto\s*(?:verify|verification)\b', r'\bfor\s*(?:verification|account\s*verification)\b'],
            'Transaction': [r'\bto\s*(?:complete|authorize)\s*(?:transaction|payment)\b'],
            'Payment': [r'for\s*payment'],
        }

        # --- Security warning patterns ---
        self.security_patterns = [
            r'\bdo\s*not\s*share\b',
            r'\bnever\s*share\b', 
        ]

        # --- Compile all patterns for performance ---
        self.compiled_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.otp_patterns]
        self.compiled_true_otp_patterns = [re.compile(p, re.IGNORECASE) for p in self.true_otp_patterns]
        self.compiled_strong_exclusions = [re.compile(p, re.IGNORECASE) for p in self.strong_exclusion_patterns]
        self.compiled_expiry_patterns = [re.compile(p, re.IGNORECASE) for p in self.expiry_patterns]
        self.compiled_security_patterns = [re.compile(p, re.IGNORECASE) for p in self.security_patterns]
        
        self.compiled_company_patterns = {}
        for company, patterns in self.company_patterns.items():
            self.compiled_company_patterns[company] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self.compiled_purpose_patterns = {}
        for purpose, patterns in self.purpose_patterns.items():
            self.compiled_purpose_patterns[purpose] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def clean_text(self, text: str) -> str:
        if pd.isna(text): return ""
        return str(text).strip()
        
    def extract_otp_code(self, text: str) -> Optional[str]:
        for pattern in self.compiled_otp_patterns:
            match = pattern.search(text)
            if match:
                otp = match.group(1)
                return re.sub(r'[- ]', '', otp)
        
        if any(p.search(text.lower()) for p in self.compiled_true_otp_patterns):
            potential_otps = re.findall(r'\b\d{4,8}\b', text)
            if potential_otps:
                return potential_otps[0]
            potential_alpha_otps = re.findall(r'\b[A-Z0-9]{4,8}\b', text)
            if potential_alpha_otps:
                 return potential_alpha_otps[0]

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

    def extract_purpose(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for purpose, patterns in self.compiled_purpose_patterns.items():
            if any(p.search(text_lower) for p in patterns):
                return purpose
        return None
        
    def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
        for pattern in self.compiled_expiry_patterns:
            match = pattern.search(text)
            if match:
                unit = match.group(2).lower()
                if unit.startswith('min'):
                    normalized_unit = 'minute'
                elif unit.startswith('sec'):
                    normalized_unit = 'second'
                elif unit.startswith('hr'):
                    normalized_unit = 'hour'
                else:
                    normalized_unit = unit.rstrip('s')

                return {
                    'duration': match.group(1),
                    'unit': normalized_unit,
                    'full_text': match.group(0)
                }
        return None

    def extract_security_warnings(self, text: str) -> List[str]:
        warnings = []
        for pattern in self.compiled_security_patterns:
            match = pattern.search(text)
            if match:
                warnings.append(match.group(0))
        return warnings

    def parse_single_message(self, message: str, sender_name: str = "") -> Dict:
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        
        confidence_score = self.calculate_otp_confidence_score(combined_text)
        
        if confidence_score >= 50:
            otp_code = self.extract_otp_code(clean_message)
            if otp_code:
                result = {
                    'status': 'parsed',
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
            'reason': 'Message did not meet the confidence threshold for an OTP.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    def process_csv_file(self, input_file: str, output_file: str = None) -> Dict:
        print("Enhanced OTP Message Parser - Analyzing Messages for OTP Content")
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
        
        print(f"Analyzing {len(df):,} messages for OTP content...")
        
        otp_messages = []
        rejected_messages = []
        
        print("Starting message analysis...")
        parse_start = time.time()
        
        batch_size = 1000
        total_messages = len(df)
        
        for i in range(0, total_messages, batch_size):
            end_idx = min(i + batch_size, total_messages)
            
            for idx in range(i, end_idx):
                row = df.iloc[idx]
                message = row['message'] if pd.notna(row['message']) else ""
                sender = row['sender_name'] if pd.notna(row['sender_name']) else ""
                
                parsed_result = self.parse_single_message(message, sender)
                parsed_result['original_index'] = idx
                
                if parsed_result['status'] == 'parsed':
                    otp_messages.append(parsed_result)
                else:
                    rejected_messages.append(parsed_result)
            
            progress = (end_idx / total_messages) * 100
            elapsed = time.time() - parse_start
            rate = end_idx / elapsed if elapsed > 0 else 0
            
            if (end_idx % 10000 == 0) or (end_idx == total_messages):
                print(f"Progress: {progress:.1f}% ({end_idx:,}/{total_messages:,}) | "
                      f"Rate: {rate:.0f} msgs/sec | "
                      f"OTP Found: {len(otp_messages):,} | "
                      f"Rejected: {len(rejected_messages):,}")
        
        parse_time = time.time() - parse_start
        print(f"\nAnalysis completed in {parse_time/60:.1f} minutes")
        
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'otp_messages_found': len(otp_messages),
                'rejected_messages': len(rejected_messages),
                'otp_detection_rate': round((len(otp_messages) / total_messages) * 100, 2) if total_messages > 0 else 0,
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '5.0_alphanumeric_support'
            },
            'summary_statistics': self.generate_summary_stats(otp_messages),
            'otp_messages': otp_messages,
            'sample_rejected_messages': rejected_messages[:10]
        }
        
        self.display_parsing_summary(results)
        
        if output_file is None:
            base_name = input_file.replace('.csv', '')
            output_file = f"{base_name}_otp_parsed.json"
        
        print(f"\nSaving results to: {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("Results saved successfully!")
        except Exception as e:
            print(f"Error saving results: {e}")
            return None
        
        return results

    def generate_summary_stats(self, otp_messages: List[Dict]) -> Dict:
        if not otp_messages:
            return {}
        
        total_otp = len(otp_messages)
        
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

    def display_parsing_summary(self, results: Dict):
        metadata = results['metadata']
        stats = results.get('summary_statistics', {})
        
        print("\n" + "="*80)
        print("OTP PARSING RESULTS SUMMARY")
        print("="*80)
        
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"Messages Rejected: {metadata['rejected_messages']:,}")
        print(f"OTP Detection Rate: {metadata['otp_detection_rate']}%")
        
        if not stats:
            print("\nNo OTP messages found to analyze.")
            return
        
        distributions = stats.get('distributions', {})
        quality_metrics = stats.get('quality_metrics', {})
        
        print("\n" + "="*60)
        print("TOP COMPANIES/SERVICES")
        print("="*60)
        
        if distributions.get('top_companies'):
            for company, count in list(distributions.get('top_companies', {}).items())[:10]:
                percentage = (count / metadata['otp_messages_found']) * 100
                print(f"{company}: {count:,} ({percentage:.1f}%)")
        else:
            print("No companies identified.")
        
        print("\n" + "="*60)
        print("QUALITY METRICS")
        print("="*60)
        
        print(f"Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")

    def test_enhanced_parser(self):
        """A comprehensive test suite to validate parser accuracy."""
        test_cases = [
            # --- NEW: Test cases for updated patterns ---
            ("1G24X3 is your OTP. Please do not share this code with anyone else. WMSSPL", "1G24X3"), # Alphanumeric
            ("Your Swiggy code: 5678. It will expire in 10 minutes.", "5678"), # "code:" format
            ("Your verification pin is 990011 for transaction.", "990011"), # "pin is" format
            ("Your one time password is: AB34CD56", "AB34CD56"), # Alphanumeric with "is:"

            # --- Existing False Positives (Should be REJECTED) ---
            ("Thank you for your order #567890 from Zomato.", None),
            ("Flash Sale! Get 50% off on orders above Rs. 1500. Use code SAVE50.", None),
            ("Your account balance is INR 12,345.67 as of 29-Aug-2025.", None),

            # --- Existing True Positives (Should be PARSED) ---
            ("OTP for Aarogya Setu is 1357. Stay safe.", "1357"),
            ("Your Discord verification code is 887766", "887766"),
            ("Your Signal registration code is 246-810.", "246810"),
            ("123 456 is your Instagram login code. Don't share it.", "123456"),
        ]

        print("--- Running High-Precision Parser Test Suite ---")
        correct_count = 0
        for i, (message, expected_otp) in enumerate(test_cases):
            result = self.parse_single_message(message)
            is_correct = False
            if result['status'] == 'parsed' and result['otp_code'] == expected_otp:
                is_correct = True
            elif result['status'] == 'rejected' and expected_otp is None:
                is_correct = True
            
            if is_correct:
                correct_count += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            print(f"\nTest {i+1}: {status}")
            print(f"  Message: '{message}'")
            print(f"  Result: {result.get('status')}, OTP: {result.get('otp_code')}, Score: {result.get('confidence_score')}")
            
        print(f"\n--- Test Complete: {correct_count}/{len(test_cases)} Passed ---")

    def interactive_message_analyzer(self):
        print("\nInteractive OTP Message Analyzer")
        print("=" * 50)
        print("Enter messages to analyze (type 'quit' to exit)")
        
        while True:
            print("\n" + "-" * 50)
            message = input("Enter message: ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                break
            
            if not message:
                continue
            
            sender = input("Enter sender name (optional): ").strip()
            
            print("\nDetailed Analysis:")
            print("-" * 30)
            
            result = self.parse_single_message(message, sender)
            
            print(f"Confidence Score: {result['confidence_score']}")
            print(f"Final Status: {result['status']}")
            
            if result['status'] == 'parsed':
                print(f"OTP Code: {result.get('otp_code')}")
                print(f"Company: {result.get('company_name')}")
            else:
                print(f"Rejection Reason: {result.get('reason')}")

def main():
    parser = EnhancedOTPMessageParser()
    
    print("Enhanced OTP Message Parser with Smart Classification")
    print("=" * 80)
    
    test_parser = input("\nWould you like to test the parser with sample messages? (y/n): ").lower().strip()
    if test_parser == 'y':
        parser.test_enhanced_parser()
    
    interactive_test = input("\nWould you like to test individual messages interactively? (y/n): ").lower().strip()
    if interactive_test == 'y':
        parser.interactive_message_analyzer()
    
    process_csv = input(f"\nWould you like to process a CSV file? (y/n): ").lower().strip()
    if process_csv == 'y':
        input_file = input("Enter the path to your CSV file: ").strip().strip('"')
        if not input_file:
            print("No file path provided. Exiting.")
            return
        
        output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
        if not output_file:
            output_file = None
        
        results = parser.process_csv_file(input_file, output_file)
        
        if results:
            print(f"\nProcessing completed successfully!")
        else:
            print("Processing failed. Please check your file path and format.")

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
#         # OTP extraction patterns (capture groups for the actual OTP number)
#         self.otp_patterns = [
#             # New, more specific patterns for Google, Banks, etc.
#             r'\b[gG]-(\d{6})\b',
#             r'(?:is|:|is:)\s*(\d{4,8})',
#             r'\b(?:otp|code|verification\s*code)\s*(?:is|:)?\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*your\s*(?:google\s*)?(?:verification\s*)?code',

#             # Existing patterns
#             r'\b(?:one[- ]?time[- ]?password|otp)\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
#             r'<#>\s*your\s*one[- ]?time[- ]?password\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
#             r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
#         ]
        
#         # Enhanced OTP classification patterns from classifier
#         self.true_otp_patterns = [
#              # New patterns
#             r'\b[gG]-(\d{6})\b',
#             r'google\s*verification\s*code',
#             r'verification\s*code\s*is\s*\d{4,8}',
#             r'otp\s*for\s*transaction',
#             r'your\s*(?:swiggy|zomato|paytm)\s*otp',
            
#             # Existing patterns
#             r'\b(?:one[- ]?time[- ]?password|otp)\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
#             r'<#>\s*your\s*one[- ]?time[- ]?password\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
#             r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
#             r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
#             r'(\d{4,8}).*(?:valid\s*for|expires?\s*in)\s*\d+\s*(?:minutes?|mins?)\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*is\s*(\d{4,8}).*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
#         ]
        
#         # Banking/Transaction exclusion patterns (should NOT be classified as OTP)
#         self.banking_exclusion_patterns = [
#             r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+',
#             r'\btotal\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
#             r'\bclr\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
#             r'\bavailable\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
#             r'\ba/c\s*\d+.*(?:credited|debited).*rs\.?\s*[\d,]+',
#             r'\bnever\s*share\s*otp.*(?:emi\s*postponement|any\s*reason).*-\w+$',
#             r'\bcard\s*details/otp/cvv\s*are\s*secret',
#             r'\bif\s*not\s*done\s*by\s*you.*report.*bank',
#         ]
        
#         # Promotional/Notification exclusion patterns
#         self.promotional_exclusion_patterns = [
#             r'\b\d+%\s*daily\s*data\s*quota\s*used\b',
#             r'\bdata\s*quota\s*(?:used|consumed|remaining)\b',
#             r'\binternet\s*speed\s*will\s*be\s*reduced\b',
#             r'\bto\s*continue\s*enjoying\s*high\s*speed\s*internet\b',
#             r'\bclick\s*https?://\w+.*recharge\b',
#             r'\bwebinar\s*:\s*(?:exploring|all\s*about)',
#             r'\b(?:register|attend)\s*(?:now|on)\s*.*https?://\b',
#             r'\bmit-wpu|vidyalankar|university|college|institute\b',
#             r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b',
#             r'\breset\s*your\s*password\s*:\s*https?://\b',
#             r'\bregistration\s*is\s*initiated\s*for\b(?!.*otp\s*\d)',
#         ]
        
#         # Expiry/validity patterns
#         self.expiry_patterns = [
#             r'\bvalid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
#             r'\bexpires?\s*in\s*(\d+)\s*(minutes?|mins?|min)\b',
#             r'\bis\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
#             r'\bonly\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
#             r'\bvalidity\s*:\s*(\d+)\s*(minutes?|mins?|min)\b',
#             r'\bthis\s*otp\s*is\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
#         ]
        
#         # Company/Service name patterns with fuzzy matching support
#         self.company_patterns = {
#             'Google': [r'\bgoogle\b'],
#             'UTS Mobile Ticket': [r'\buts\s*mobile\s*ticket\b', r'\buts\b'],
#             'CRIS': [r'\bcris\b'],
#             'Dream11': [r'\bdream11\b', r'\bdream\s*11\b'],
#             'Paytm': [r'\bpaytm\b'],
#             'PhonePe': [r'\bphonepe\b', r'\bphone\s*pe\b'],
#             'Zupee': [r'\bzupee\b'],
#             'Meesho': [r'\bmeesho\b'],
#             'AJIO': [r'\bajio\b'],
#             'Google Pay': [r'\bgoogle\s*pay\b', r'\bgpay\b'],
#             'Amazon': [r'\bamazon\b'],
#             'Flipkart': [r'\bflipkart\b'],
#             'Myntra': [r'\bmyntra\b'],
#             'Swiggy': [r'\bswiggy\b'],
#             'Zomato': [r'\bzomato\b'],
#             'Ola': [r'\bola\b(?!\s*(?:money|electric))'],
#             'Uber': [r'\buber\b'],
#             'BigBasket': [r'\bbigbasket\b', r'\bbig\s*basket\b'],
#             'BookMyShow': [r'\bbookmyshow\b', r'\bbook\s*my\s*show\b'],
#             'MakeMyTrip': [r'\bmakemytrip\b', r'\bmake\s*my\s*trip\b'],
#             'ICICI Bank': [r'\bicici\b'],
#             'HDFC': [r'\bhdfc\b'],
#             'SBI': [r'\bsbi\b', r'\bstate\s*bank\s*of\s*india\b'],
#             'Axis Bank': [r'\baxis\s*bank\b'],
#             'Jio': [r'\bjio\b'],
#             'Airtel': [r'\bairtel\b'],
#             'Vi': [r'\bvi\b(?:\s|$)', r'\bvodafone\s*idea\b'],
#             'WhatsApp': [r'\bwhatsapp\b', r'\bwhats\s*app\b'],
#             'Facebook': [r'\bfacebook\b'],
#             'Instagram': [r'\binstagram\b'],
#         }
        
#         # Purpose/Action patterns
#         self.purpose_patterns = {
#             'Login': [r'\bto\s*(?:login|log\s*in|sign\s*in)\b', r'\bfor\s*(?:login|log\s*in|sign\s*in)\b'],
#             'Registration': [r'\bto\s*(?:register|registration|sign\s*up)\b', r'\bfor\s*(?:registration|sign\s*up)\b'],
#             'Verification': [r'\bto\s*(?:verify|verification)\b', r'\bfor\s*(?:verification|account\s*verification)\b'],
#             'Proceed': [r'\bto\s*proceed\b'],
#             'Reset Password': [r'\bto\s*reset\s*(?:password|pin)\b', r'\bpassword\s*reset\b'],
#             'Transaction': [r'\bto\s*(?:complete|authorize)\s*(?:transaction|payment)\b'],
#             'Convert': [r'\bto\s*convert\s*connection\s*type\b'],
#             'Mobile Ticket': [r'for\s*uts\s*mobile\s*ticket'], # New purpose
#         }
        
#         # Security warning patterns
#         self.security_patterns = [
#             r'\bdo\s*not\s*share\b',
#             r'\bnever\s*share\b', 
#             r'\bnever\s*call\b',
#             r'\bnever\s*message\b',
#             r'\bwill\s*never\s*call\b',
#             r'\bkeep\s*your\s*account\s*safe\b',
#             r'\bfor\s*security\s*reasons\b',
#             r'\bgives\s*them\s*full\s*access\b',
#         ]
        
#         # Compile all patterns for better performance
#         self.compiled_otp_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.otp_patterns]
#         self.compiled_true_otp_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.true_otp_patterns]
#         self.compiled_banking_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.banking_exclusion_patterns]
#         self.compiled_promotional_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.promotional_exclusion_patterns]
#         self.compiled_expiry_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.expiry_patterns]
#         self.compiled_security_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.security_patterns]
        
#         # Compile company patterns
#         self.compiled_company_patterns = {}
#         for company, patterns in self.company_patterns.items():
#             self.compiled_company_patterns[company] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
#         # Compile purpose patterns
#         self.compiled_purpose_patterns = {}
#         for purpose, patterns in self.purpose_patterns.items():
#             self.compiled_purpose_patterns[purpose] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

#     def clean_text(self, text: str) -> str:
#         """Clean and normalize text for better matching"""
#         if pd.isna(text):
#             return ""
        
#         text = str(text).strip()
#         text = re.sub(r'\s+', ' ', text)
#         return text

#     def has_actual_otp_number(self, text: str) -> bool:
#         """Check if text contains an actual OTP number (4-8 digits)"""
#         otp_number_patterns = [
#             r'\b\d{4,8}\b.*\b(?:otp|one\s*time\s*password|code)\b',
#             r'\b(?:otp|one\s*time\s*password|code)\b.*\b\d{4,8}\b',
#             r'\b[gG]-\d{6}\b',
#         ]
        
#         for pattern in otp_number_patterns:
#             if re.search(pattern, text, re.IGNORECASE):
#                 return True
        
#         return False

#     def has_strong_otp_indicators(self, text: str) -> bool:
#         """Check for strong OTP-specific language patterns"""
#         text_lower = text.lower()
        
#         strong_otp_phrases = [
#             'is your otp', 'is the otp', 'otp is', 'one time password is',
#             'your otp for', 'otp for your', 'to proceed on', 'otp to login',
#             'otp to register', 'use one time password', 'your one time password',
#             'verification code', 'confirmation code', 'your code is'
#         ]
        
#         return any(phrase in text_lower for phrase in strong_otp_phrases)

#     def has_security_context(self, text: str) -> bool:
#         """Check for OTP security warnings"""
#         text_lower = text.lower()
        
#         security_phrases = [
#             'do not share', 'never call', 'never message', 'will never call',
#             'never calls you', 'keep your account safe', 'for security reasons',
#             'gives them full access'
#         ]
        
#         has_security = any(phrase in text_lower for phrase in security_phrases)
#         has_otp_num = self.has_actual_otp_number(text)
        
#         return has_security and has_otp_num

#     def has_validity_context(self, text: str) -> bool:
#         """Check for OTP validity/expiry context"""
#         validity_patterns = [
#             r'\bvalid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
#             r'\bexpires?\s*in\s*\d+\s*(?:minutes?|mins?)\b',
#             r'\bis\s*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
#         ]
        
#         for pattern in validity_patterns:
#             if re.search(pattern, text, re.IGNORECASE):
#                 return True
        
#         return False

#     def is_strong_banking_context(self, text: str) -> bool:
#         """Check for strong banking context that should exclude OTP classification"""
#         # Weaken this for OTPs that mention transactions
#         if 'otp for transaction' in text.lower():
#             return False

#         text_lower = text.lower()
        
#         if re.search(r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+', text_lower):
#             return True
#         if re.search(r'\b(?:total|clr|available)\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+', text_lower):
#             return True
#         if re.search(r'\ba/c\s*\w+.*(?:credited|debited)', text_lower):
#             return True
#         if 'emi postponement' in text_lower and 'never share otp' in text_lower:
#             return True
#         if 'card details/otp/cvv are secret' in text_lower:
#             return True
        
#         return False

#     def is_promotional_message(self, text: str) -> bool:
#         """Check if message is promotional/notification rather than OTP"""
#         text_lower = text.lower()
        
#         strong_promotional = [
#             'data quota used', 'webinar:', 'tap to reset', 'registration is initiated',
#             'exploring the field', 'exam dates, registration, eligibility'
#         ]
        
#         for indicator in strong_promotional:
#             if indicator in text_lower:
#                 return True
        
#         if re.search(r'\b\d+%\s*(?:daily\s*)?data\s*quota\s*used\b', text_lower):
#             return True
#         if re.search(r'\bwebinar\s*:.*(?:exploring|all\s*about)', text_lower):
#             return True
#         if re.search(r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b', text_lower):
#             return True
#         if re.search(r'\bregistration\s*is\s*initiated\s*for\b', text_lower) and not self.has_actual_otp_number(text):
#             return True
        
#         return False

#     def is_true_otp_message(self, text: str) -> bool:
#         """Enhanced method to determine if this is a genuine OTP message"""
        
#         # Must have actual OTP number
#         if not self.has_actual_otp_number(text):
#             return False
        
#         # Check for strong banking context first (exclusion)
#         if self.is_strong_banking_context(text):
#             return False
        
#         # Check for promotional content (exclusion)
#         if self.is_promotional_message(text):
#             return False
        
#         # Apply exclusion patterns
#         for pattern in self.compiled_banking_exclusions:
#             if pattern.search(text) and 'otp for transaction' not in text.lower():
#                 return False
        
#         for pattern in self.compiled_promotional_exclusions:
#             if pattern.search(text):
#                 return False
        
#         # Check for strong OTP indicators
#         if self.has_strong_otp_indicators(text):
#             return True
        
#         # Check for security context
#         if self.has_security_context(text):
#             return True
        
#         # Check for validity context with OTP
#         if self.has_validity_context(text) and 'otp' in text.lower():
#             return True
        
#         # Platform-specific patterns
#         text_lower = text.lower()
#         platforms = ['dream11', 'zupee', 'paytm', 'meesho', 'phonepe', 'ajio', 'jio', 'uts', 'google', 'amazon', 'flipkart', 'swiggy', 'zomato', 'hdfc']
        
#         for platform in platforms:
#             if platform in text_lower:
#                 if any(word in text_lower for word in ['account', 'login', 'register', 'proceed', 'ticket', 'verification', 'transaction']):
#                     return True
        
#         # Check true OTP patterns
#         otp_pattern_matches = sum(1 for pattern in self.compiled_true_otp_patterns if pattern.search(text))
#         if otp_pattern_matches >= 1:
#             return True
        
#         return False

#     def fuzzy_match_company(self, text: str, threshold: float = 0.8) -> Optional[str]:
#         """Use fuzzy matching to identify company names"""
#         text_words = re.findall(r'\b\w+\b', text.lower())
        
#         for company in self.company_patterns.keys():
#             company_lower = company.lower()
            
#             # Direct fuzzy matching
#             for word in text_words:
#                 ratio = SequenceMatcher(None, word, company_lower).ratio()
#                 if ratio >= threshold:
#                     return company
            
#             # Check for partial matches in company name
#             for part in company_lower.split():
#                 if len(part) >= 3:  # Only check meaningful parts
#                     for word in text_words:
#                         if len(word) >= 3:
#                             ratio = SequenceMatcher(None, word, part).ratio()
#                             if ratio >= threshold:
#                                 return company
        
#         return None

#     def extract_otp_code(self, text: str) -> Optional[str]:
#         """Extract OTP code from message with enhanced patterns"""
#         if pd.isna(text):
#             return None
        
#         text = str(text).strip()
        
#         # Try each OTP pattern
#         for pattern in self.compiled_otp_patterns:
#             match = pattern.search(text)
#             if match and match.groups():
#                 return match.group(1)
        
#         # Fallback patterns
#         fallback_patterns = [
#             r'\b(\d{4,8})\b.*(?:otp|one\s*time\s*password|code)',
#             r'(?:otp|one\s*time\s*password|code).*\b(\d{4,8})\b',
#             r'\b(\d{4,8})\b', # Last resort: find any 4-8 digit number
#         ]
        
#         for pattern in fallback_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return match.group(1)
        
#         return None

#     def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
#         """Extract expiry time information"""
#         if pd.isna(text):
#             return None
        
#         text = str(text).strip()
        
#         for pattern in self.compiled_expiry_patterns:
#             match = pattern.search(text)
#             if match:
#                 return {
#                     'duration': match.group(1),
#                     'unit': match.group(2),
#                     'full_text': match.group(0)
#                 }
        
#         return None

#     def extract_company_name(self, text: str, sender_name: str = "") -> Optional[str]:
#         """Extract company/service name with regex and fuzzy matching"""
#         if pd.isna(text):
#             text = ""
#         if pd.isna(sender_name):
#             sender_name = ""
        
#         combined_text = f"{str(text)} {str(sender_name)}"
        
#         # First try exact regex patterns
#         for company, patterns in self.compiled_company_patterns.items():
#             for pattern in patterns:
#                 if pattern.search(combined_text):
#                     return company
        
#         # Try fuzzy matching
#         fuzzy_company = self.fuzzy_match_company(combined_text)
#         if fuzzy_company:
#             return fuzzy_company
        
#         # Extract from sender patterns
#         sender_patterns = [
#             r'([A-Z][A-Za-z]+)(?:-|\s|$)',
#             r'([A-Z]{2,})',
#         ]
        
#         for pattern in sender_patterns:
#             match = re.search(pattern, sender_name)
#             if match and len(match.group(1)) >= 2:
#                 return match.group(1)
        
#         return None

#     def extract_purpose(self, text: str) -> Optional[str]:
#         """Extract the purpose of the OTP"""
#         if pd.isna(text):
#             return None
        
#         text = str(text).strip()
        
#         for purpose, patterns in self.compiled_purpose_patterns.items():
#             for pattern in patterns:
#                 if pattern.search(text):
#                     return purpose
        
#         return None

#     def extract_security_warnings(self, text: str) -> List[str]:
#         """Extract security warning messages"""
#         if pd.isna(text):
#             return []
        
#         text = str(text).strip()
#         warnings = []
        
#         for pattern in self.compiled_security_patterns:
#             match = pattern.search(text)
#             if match:
#                 warnings.append(match.group(0))
        
#         return warnings

#     def extract_reference_id(self, text: str) -> Optional[str]:
#         """Extract reference ID, transaction ID, or order number"""
#         if pd.isna(text):
#             return None
        
#         text = str(text).strip()
        
#         ref_patterns = [
#             r'\bid\s*:\s*([A-Za-z0-9/_]+)',
#             r'\bref\s*(?:id|no|number)\s*[:|-]\s*([A-Za-z0-9/_]+)',
#             r'\border\s*(?:number|no)\s*:\s*([A-Za-z0-9]+)',
#             r'\btxn\s*(?:id|no)\s*:\s*([A-Za-z0-9]+)',
#             r'\btransaction\s*(?:id|no)\s*:\s*([A-Za-z0-9]+)',
#             r'\breference\s*:\s*([A-Za-z0-9]+)',
#         ]
        
#         for pattern in ref_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 ref_id = match.group(1).strip()
#                 if 3 <= len(ref_id) <= 20:
#                     return ref_id
        
#         return None

#     def extract_phone_number(self, text: str) -> Optional[str]:
#         """Extract phone number if mentioned in the message"""
#         if pd.isna(text):
#             return None
        
#         text = str(text).strip()
        
#         phone_patterns = [
#             r'\bjio\s*number\s*:\s*(\d{10})\b',
#             r'\bmobile\s*(?:number|no)\s*:\s*(\d{10})\b',
#             r'\bphone\s*(?:number|no)\s*:\s*(\d{10})\b',
#             r'\bnumber\s*(\d{10})\b',
#             r'\b(\d{10})\b(?=\s*(?:from|for|$))',
#         ]
        
#         for pattern in phone_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return match.group(1)
        
#         return None

#     def extract_sender_info(self, sender_name: str) -> Dict[str, str]:
#         """Extract information from sender name/ID"""
#         if pd.isna(sender_name):
#             return {'sender_type': None, 'sender_clean': None}
        
#         sender_clean = str(sender_name).strip()
        
#         # Determine sender type
#         if re.match(r'^[A-Z]{2}-', sender_clean):
#             sender_type = "Short Code"
#         elif re.match(r'^[A-Z]+$', sender_clean):
#             sender_type = "Alpha Code"
#         elif re.match(r'^\d+$', sender_clean):
#             sender_type = "Numeric"
#         else:
#             sender_type = "Mixed"
        
#         return {
#             'sender_type': sender_type,
#             'sender_clean': sender_clean
#         }

#     def calculate_otp_confidence_score(self, text: str, sender_name: str = "") -> float:
#         """Calculate confidence score for OTP classification"""
#         combined_text = f"{text} {sender_name}"
#         score = 0.0
        
#         # Base OTP indicators (40 points)
#         if self.has_actual_otp_number(combined_text):
#             score += 40
        
#         # Strong OTP language (30 points)
#         if self.has_strong_otp_indicators(combined_text):
#             score += 30
        
#         # Security context (20 points)
#         if self.has_security_context(combined_text):
#             score += 20
        
#         # Validity context (10 points)
#         if self.has_validity_context(combined_text):
#             score += 10
        
#         # Pattern matching bonus
#         pattern_matches = sum(1 for pattern in self.compiled_true_otp_patterns if pattern.search(combined_text))
#         score += min(pattern_matches * 10, 30)  # Max 30 bonus points
        
#         # Penalties for exclusions
#         if self.is_strong_banking_context(combined_text):
#             score -= 50
        
#         if self.is_promotional_message(combined_text):
#             score -= 30
        
#         return max(0, min(100, score))  # Ensure score is between 0-100

#     def parse_single_message(self, message: str, sender_name: str = "") -> Dict:
#         """Parse a single message and extract all relevant information"""
        
#         # Clean inputs
#         clean_message = self.clean_text(message)
#         clean_sender = self.clean_text(sender_name)
#         combined_text = f"{clean_message} {clean_sender}"
        
#         # Calculate confidence score
#         confidence_score = self.calculate_otp_confidence_score(clean_message, clean_sender)
        
#         # Determine if this is an OTP message (threshold: 40)
#         is_otp_message = confidence_score >= 40 and self.is_true_otp_message(combined_text)
        
#         if not is_otp_message:
#             return {
#                 'status': 'rejected',
#                 'reason': 'Message not related to Security & Authentication - OTP verification',
#                 'confidence_score': confidence_score,
#                 'message_preview': clean_message[:100] + "..." if len(clean_message) > 100 else clean_message
#             }
        
#         # Extract sender information
#         sender_info = self.extract_sender_info(sender_name)
        
#         # Parse OTP information
#         result = {
#             'status': 'parsed',
#             'confidence_score': confidence_score,
#             'otp_code': self.extract_otp_code(clean_message),
#             'company_name': self.extract_company_name(clean_message, clean_sender),
#             'purpose': self.extract_purpose(clean_message),
#             'expiry_info': self.extract_expiry_time(clean_message),
#             'security_warnings': self.extract_security_warnings(clean_message),
#             'reference_id': self.extract_reference_id(clean_message),
#             'phone_number': self.extract_phone_number(clean_message),
#             'sender_name': clean_sender if clean_sender else None,
#             'sender_type': sender_info['sender_type'],
#             'sender_clean': sender_info['sender_clean'],
#             'raw_message': clean_message,
#             'message_length': len(clean_message),
#             'contains_url': bool(re.search(r'https?://\S+', clean_message)),
#         }
        
#         # Format expiry info for better display
#         if result['expiry_info']:
#             result['expiry_duration'] = f"{result['expiry_info']['duration']} {result['expiry_info']['unit']}"
#             result['expiry_full_text'] = result['expiry_info']['full_text']
#         else:
#             result['expiry_duration'] = None
#             result['expiry_full_text'] = None
        
#         # Convert security warnings list to string
#         if result['security_warnings']:
#             result['security_warnings_text'] = "; ".join(result['security_warnings'])
#         else:
#             result['security_warnings_text'] = None
        
#         return result

#     def process_csv_file(self, input_file: str, output_file: str = None) -> Dict:
#         """Process CSV file and extract OTP information from messages"""
        
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
        
#         # Check required columns
#         if 'message' not in df.columns:
#             print("Error: 'message' column not found")
#             return None
        
#         # Ensure sender_name column exists
#         if 'sender_name' not in df.columns:
#             print("Warning: 'sender_name' column not found. Using empty values.")
#             df['sender_name'] = ""
        
#         print(f"Analyzing {len(df):,} messages for OTP content...")
        
#         # Initialize results
#         otp_messages = []
#         rejected_messages = []
        
#         print("Starting message analysis...")
#         parse_start = time.time()
        
#         # Process messages in batches
#         batch_size = 1000
#         total_messages = len(df)
        
#         for i in range(0, total_messages, batch_size):
#             end_idx = min(i + batch_size, total_messages)
            
#             # Process batch
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
            
#             # Progress update
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
        
#         # Generate comprehensive results
#         results = {
#             'metadata': {
#                 'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
#                 'total_input_messages': int(total_messages),
#                 'otp_messages_found': len(otp_messages),
#                 'rejected_messages': len(rejected_messages),
#                 'otp_detection_rate': round((len(otp_messages) / total_messages) * 100, 2),
#                 'processing_time_minutes': round(parse_time / 60, 2),
#                 'parser_version': '2.2_updated' # Version updated
#             },
#             'summary_statistics': self.generate_summary_stats(otp_messages),
#             'otp_messages': otp_messages,
#             'sample_rejected_messages': rejected_messages[:10]  # Include sample of rejected messages
#         }
        
#         # Display summary
#         self.display_parsing_summary(results)
        
#         # Save results
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
#         """Generate comprehensive summary statistics"""
        
#         if not otp_messages:
#             return {}
        
#         total_otp = len(otp_messages)
        
#         # Extract statistics
#         otp_codes_found = sum(1 for msg in otp_messages if msg.get('otp_code'))
#         companies_identified = sum(1 for msg in otp_messages if msg.get('company_name'))
#         purposes_identified = sum(1 for msg in otp_messages if msg.get('purpose'))
#         expiry_found = sum(1 for msg in otp_messages if msg.get('expiry_info'))
#         security_warnings = sum(1 for msg in otp_messages if msg.get('security_warnings'))
#         reference_ids = sum(1 for msg in otp_messages if msg.get('reference_id'))
#         phone_numbers = sum(1 for msg in otp_messages if msg.get('phone_number'))
        
#         # Company distribution
#         companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
#         company_counts = {}
#         for company in companies:
#             company_counts[company] = company_counts.get(company, 0) + 1
        
#         # Purpose distribution
#         purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
#         purpose_counts = {}
#         for purpose in purposes:
#             purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        
#         # Expiry distribution
#         expiry_durations = [msg.get('expiry_duration') for msg in otp_messages if msg.get('expiry_duration')]
#         expiry_counts = {}
#         for duration in expiry_durations:
#             expiry_counts[duration] = expiry_counts.get(duration, 0) + 1
        
#         # Confidence score distribution
#         confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
#         avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
#         return {
#             'extraction_rates': {
#                 'otp_codes_extracted': round((otp_codes_found / total_otp) * 100, 2),
#                 'companies_identified': round((companies_identified / total_otp) * 100, 2),
#                 'purposes_identified': round((purposes_identified / total_otp) * 100, 2),
#                 'expiry_info_found': round((expiry_found / total_otp) * 100, 2),
#                 'security_warnings_found': round((security_warnings / total_otp) * 100, 2),
#                 'reference_ids_found': round((reference_ids / total_otp) * 100, 2),
#                 'phone_numbers_found': round((phone_numbers / total_otp) * 100, 2),
#             },
#             'distributions': {
#                 'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
#                 'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
#                 'expiry_durations': dict(sorted(expiry_counts.items(), key=lambda x: x[1], reverse=True)),
#             },
#             'quality_metrics': {
#                 'average_confidence_score': round(avg_confidence, 2),
#                 'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
#                 'medium_confidence_messages': sum(1 for score in confidence_scores if 40 <= score < 80),
#                 'low_confidence_messages': sum(1 for score in confidence_scores if score < 40),
#             }
#         }

#     def display_parsing_summary(self, results: Dict):
#         """Display comprehensive parsing summary"""
        
#         metadata = results['metadata']
#         stats = results.get('summary_statistics', {})
        
#         print("\n" + "="*80)
#         print("OTP PARSING RESULTS SUMMARY")
#         print("="*80)
        
#         print(f"Total Input Messages: {metadata['total_input_messages']:,}")
#         print(f"OTP Messages Found: {metadata['otp_messages_found']:,}")
#         print(f"Messages Rejected: {metadata['rejected_messages']:,}")
#         print(f"OTP Detection Rate: {metadata['otp_detection_rate']}%")
#         print(f"Processing Time: {metadata['processing_time_minutes']} minutes")
        
#         if not stats:
#             print("\nNo OTP messages found to analyze.")
#             return
        
#         extraction_rates = stats.get('extraction_rates', {})
#         distributions = stats.get('distributions', {})
#         quality_metrics = stats.get('quality_metrics', {})
        
#         print("\n" + "="*60)
#         print("EXTRACTION ACCURACY")
#         print("="*60)
        
#         for metric, rate in extraction_rates.items():
#             print(f"{metric.replace('_', ' ').title()}: {rate}%")
        
#         print("\n" + "="*60)
#         print("TOP COMPANIES/SERVICES")
#         print("="*60)
        
#         for company, count in list(distributions.get('top_companies', {}).items())[:10]:
#             percentage = (count / metadata['otp_messages_found']) * 100
#             print(f"{company}: {count:,} ({percentage:.1f}%)")
        
#         print("\n" + "="*60)
#         print("PURPOSE DISTRIBUTION")
#         print("="*60)
        
#         for purpose, count in distributions.get('purposes', {}).items():
#             percentage = (count / metadata['otp_messages_found']) * 100
#             print(f"{purpose}: {count:,} ({percentage:.1f}%)")
        
#         print("\n" + "="*60)
#         print("QUALITY METRICS")
#         print("="*60)
        
#         print(f"Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")
#         print(f"High Confidence (≥80): {quality_metrics.get('high_confidence_messages', 0):,}")
#         print(f"Medium Confidence (40-79): {quality_metrics.get('medium_confidence_messages', 0):,}")
#         print(f"Low Confidence (<40): {quality_metrics.get('low_confidence_messages', 0):,}")

#     def test_enhanced_parser(self):
#         """Test the enhanced parser with sample messages"""
        
#         # Test messages that should be parsed as OTP
#         otp_test_messages = [
#             {'message': "G-123456 is your Google verification code.", 'sender': "Google", 'expected': 'parsed'},
#             {'message': "Your Google account verification code is 789012. Do not share it with anyone.", 'sender': "Google", 'expected': 'parsed'},
#             {'message': "Amazon OTP: 556677. Use this for your transaction. Do not share it.", 'sender': "Amazon", 'expected': 'parsed'},
#             {'message': "OTP for transaction of INR 3,500 on your HDFC Bank Card ending 1234 is 987654.", 'sender': "HDFC", 'expected': 'parsed'},
#             {'message': "Paytm: Never share this OTP with anyone. Your OTP to add money is 246810.", 'sender': "Paytm", 'expected': 'parsed'},
#             {'message': "Use OTP 135792 to log in to your Swiggy account. Enjoy your meal!", 'sender': "Swiggy", 'expected': 'parsed'},
#         ]
        
#         # Test messages that should be rejected
#         rejection_test_messages = [
#             {
#                 'message': "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517 For tips on how to manage data quota effectively, click https://youtu.be/ZFUDydctV78",
#                 'sender': "JIO",
#                 'expected': 'rejected'
#             },
#             {
#                 'message': "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR Clr Bal: Rs. 47,695.00 CR. -CBoI",
#                 'sender': "CBoI",
#                 'expected': 'rejected'
#             },
#         ]
        
#         print("\nTesting Enhanced OTP Parser:")
#         print("=" * 80)
        
#         print("\nTesting OTP Messages (should be PARSED):")
#         print("-" * 50)
        
#         otp_correct = 0
#         for i, test_case in enumerate(otp_test_messages, 1):
#             result = self.parse_single_message(test_case['message'], test_case['sender'])
#             is_correct = result['status'] == test_case['expected']
#             status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
#             if is_correct:
#                 otp_correct += 1
            
#             print(f"Test {i}: {status}")
#             print(f"Message: {test_case['message'][:80]}...")
#             print(f"Status: {result['status']}")
#             print(f"Confidence: {result.get('confidence_score', 'N/A')}")
            
#             if result['status'] == 'parsed':
#                 print(f"OTP Code: {result.get('otp_code')}")
#                 print(f"Company: {result.get('company_name')}")
#                 print(f"Purpose: {result.get('purpose')}")
            
#             print("-" * 50)
        
#         print("\nTesting Non-OTP Messages (should be REJECTED):")
#         print("-" * 50)
        
#         rejection_correct = 0
#         for i, test_case in enumerate(rejection_test_messages, 1):
#             result = self.parse_single_message(test_case['message'], test_case['sender'])
#             is_correct = result['status'] == test_case['expected']
#             status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
#             if is_correct:
#                 rejection_correct += 1
            
#             print(f"Test {i}: {status}")
#             print(f"Message: {test_case['message'][:80]}...")
#             print(f"Status: {result['status']}")
#             print(f"Confidence: {result.get('confidence_score', 'N/A')}")
#             print(f"Reason: {result.get('reason', 'N/A')}")
#             print("-" * 50)
        
#         total_correct = otp_correct + rejection_correct
#         total_tests = len(otp_test_messages) + len(rejection_test_messages)
        
#         print(f"\nTest Results Summary:")
#         print(f"OTP Detection Accuracy: {otp_correct}/{len(otp_test_messages)} ({(otp_correct/len(otp_test_messages)*100):.1f}%)")
#         print(f"Rejection Accuracy: {rejection_correct}/{len(rejection_test_messages)} ({(rejection_correct/len(rejection_test_messages)*100):.1f}%)")
#         print(f"Overall Accuracy: {total_correct}/{total_tests} ({((total_correct/total_tests)*100):.1f}%)")

#     def analyze_single_message(self, message: str, sender_name: str = "") -> Dict:
#         """Analyze a single message and return detailed breakdown"""
        
#         clean_message = self.clean_text(message)
#         clean_sender = self.clean_text(sender_name)
#         combined_text = f"{clean_message} {clean_sender}"
        
#         analysis = {
#             'message': clean_message,
#             'sender_name': clean_sender,
#             'analysis_steps': {
#                 'has_otp_number': self.has_actual_otp_number(combined_text),
#                 'strong_otp_indicators': self.has_strong_otp_indicators(combined_text),
#                 'security_context': self.has_security_context(combined_text),
#                 'validity_context': self.has_validity_context(combined_text),
#                 'banking_context': self.is_strong_banking_context(combined_text),
#                 'promotional_context': self.is_promotional_message(combined_text),
#                 'is_true_otp': self.is_true_otp_message(combined_text),
#             },
#             'confidence_score': self.calculate_otp_confidence_score(clean_message, clean_sender),
#         }
        
#         # Get final parsing result
#         parsing_result = self.parse_single_message(clean_message, clean_sender)
#         analysis['final_result'] = parsing_result
        
#         return analysis

# # ... (The rest of the file remains the same)


#     def export_detailed_report(self, results: Dict, output_prefix: str):
#         """Export detailed analysis reports"""
        
#         # Create summary report
#         summary_file = f"{output_prefix}_summary_report.json"
        
#         summary_report = {
#             'metadata': results['metadata'],
#             'summary_statistics': results['summary_statistics'],
#             'key_insights': {
#                 'most_common_companies': list(results['summary_statistics']['distributions']['top_companies'].items())[:5],
#                 'most_common_purposes': list(results['summary_statistics']['distributions']['purposes'].items()),
#                 'most_common_expiry_times': list(results['summary_statistics']['distributions']['expiry_durations'].items())[:3],
#             }
#         }
        
#         try:
#             with open(summary_file, 'w', encoding='utf-8') as f:
#                 json.dump(summary_report, f, indent=2, ensure_ascii=False)
#             print(f"Summary report saved: {summary_file}")
#         except Exception as e:
#             print(f"Error saving summary report: {e}")

#     def interactive_message_analyzer(self):
#         """Interactive tool to analyze individual messages"""
        
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
            
#             analysis = self.analyze_single_message(message, sender)
            
#             print(f"Confidence Score: {analysis['confidence_score']}")
#             print(f"Final Status: {analysis['final_result']['status']}")
            
#             if analysis['final_result']['status'] == 'parsed':
#                 result = analysis['final_result']
#                 print(f"OTP Code: {result.get('otp_code')}")
#                 print(f"Company: {result.get('company_name')}")
#                 print(f"Purpose: {result.get('purpose')}")
#                 print(f"Expiry: {result.get('expiry_duration')}")
#                 print(f"Security Warnings: {len(result.get('security_warnings', []))}")
#                 print(f"Reference ID: {result.get('reference_id')}")
#                 print(f"Phone Number: {result.get('phone_number')}")
#             else:
#                 print(f"Rejection Reason: {analysis['final_result'].get('reason')}")
            
#             print(f"\nDetailed Checks:")
#             for check, value in analysis['analysis_steps'].items():
#                 print(f"  {check.replace('_', ' ').title()}: {value}")

# def main():
#     # Initialize enhanced parser
#     parser = EnhancedOTPMessageParser()
    
#     print("Enhanced OTP Message Parser with Smart Classification")
#     print("=" * 80)
#     print("This parser analyzes messages to identify OTP content using:")
#     print("- Regex pattern matching")
#     print("- Keyword analysis")
#     print("- Fuzzy matching")
#     print("- Context-aware classification")
#     print("- Confidence scoring")
    
#     # Test parser first
#     test_parser = input("\nWould you like to test the parser with sample messages? (y/n): ").lower().strip()
    
#     if test_parser == 'y':
#         parser.test_enhanced_parser()
    
#     # Interactive analyzer
#     interactive_test = input("\nWould you like to test individual messages interactively? (y/n): ").lower().strip()
    
#     if interactive_test == 'y':
#         parser.interactive_message_analyzer()
    
#     # Process CSV file
#     process_csv = input(f"\nWould you like to process a CSV file? (y/n): ").lower().strip()
    
#     if process_csv == 'y':
#         # Get input file path
#         input_file = input("Enter the path to your CSV file: ").strip().strip('"')
        
#         if not input_file:
#             print("No file path provided. Exiting.")
#             return
        
#         # Ask for output file path
#         output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
#         if not output_file:
#             output_file = None
        
#         print(f"\nProcessing file: {input_file}")
#         print("Analyzing messages for OTP content...")
#         print("Only messages identified as OTP will be parsed and included in output.")
        
#         # Process the file
#         results = parser.process_csv_file(input_file, output_file)
        
#         if results:
#             print(f"\nProcessing completed successfully!")
            
#             # Ask for detailed report
#             detailed_report = input("\nWould you like to generate a detailed analysis report? (y/n): ").lower().strip()
#             if detailed_report == 'y':
#                 output_prefix = input_file.replace('.csv', '')
#                 parser.export_detailed_report(results, output_prefix)
            
#             # Show sample results
#             if results['metadata']['otp_messages_found'] > 0:
#                 show_samples = input("\nWould you like to see sample parsed OTP messages? (y/n): ").lower().strip()
#                 if show_samples == 'y':
#                     n_samples = min(5, len(results['otp_messages']))
                    
#                     print(f"\nSample Parsed OTP Messages ({n_samples} examples):")
#                     print("=" * 80)
                    
#                     for i, msg in enumerate(results['otp_messages'][:n_samples], 1):
#                         print(f"\nExample {i}:")
#                         print("-" * 40)
#                         print(f"OTP Code: {msg.get('otp_code')}")
#                         print(f"Company: {msg.get('company_name')}")
#                         print(f"Purpose: {msg.get('purpose')}")
#                         print(f"Validity: {msg.get('expiry_duration')}")
#                         print(f"Security Warnings: {msg.get('security_warnings_text')}")
#                         print(f"Reference ID: {msg.get('reference_id')}")
#                         print(f"Phone Number: {msg.get('phone_number')}")
#                         print(f"Sender: {msg.get('sender_name')}")
#                         print(f"Confidence: {msg.get('confidence_score')}")
                        
#                         message_preview = msg.get('raw_message', '')[:150]
#                         print(f"Message: {message_preview}{'...' if len(msg.get('raw_message', '')) > 150 else ''}")
#             else:
#                 print("\nNo OTP messages found in the dataset.")
#                 print("All messages were rejected as not related to OTP verification.")
            
#             print(f"\nFinal Summary:")
#             print(f"Input Messages: {results['metadata']['total_input_messages']:,}")
#             print(f"OTP Messages Found: {results['metadata']['otp_messages_found']:,}")
#             print(f"Detection Rate: {results['metadata']['otp_detection_rate']}%")
            
#         else:
#             print("Processing failed. Please check your file path and format.")


# if __name__ == "__main__":
#     main()