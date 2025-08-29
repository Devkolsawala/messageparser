import pandas as pd
import re
import numpy as np
from typing import Dict, List, Tuple
import time

class SMSClassifier:
    def __init__(self):
        # Define comprehensive keyword patterns with context awareness
        
        # Banking/Transaction exclusion patterns (should NOT be classified as OTP)
        # These are more specific to avoid catching legitimate OTP messages
        self.banking_exclusion_patterns = [
            r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+',  # Transaction amounts
            r'\btotal\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',   # Balance statements
            r'\bclr\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',     # Clear balance
            r'\bavailable\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+', # Available balance
            r'\ba/c\s*\d+.*(?:credited|debited).*rs\.?\s*[\d,]+',  # Account transactions
            r'\bnever\s*share\s*otp.*(?:emi\s*postponement|any\s*reason).*-\w+$',  # Bank warnings
            r'\bcard\s*details/otp/cvv\s*are\s*secret',       # Generic bank security warning
            r'\bif\s*not\s*done\s*by\s*you.*report.*bank',   # Bank fraud warning
        ]
        
        # Promotional/Notification exclusion patterns (should NOT be classified as OTP)
        self.promotional_exclusion_patterns = [
            # Data usage notifications
            r'\b\d+%\s*daily\s*data\s*quota\s*used\b',
            r'\bdata\s*quota\s*(?:used|consumed|remaining)\b',
            r'\binternet\s*speed\s*will\s*be\s*reduced\b',
            r'\bto\s*continue\s*enjoying\s*high\s*speed\s*internet\b',
            r'\bclick\s*https?://\w+.*recharge\b',
            r'\bdial\s*\d+.*(?:balance|validity|plan\s*details)\b',
            
            # Webinar/Educational notifications
            r'\bwebinar\s*:\s*(?:exploring|all\s*about)',
            r'\b(?:register|attend)\s*(?:now|on)\s*.*https?://\b',
            r'\bmit-wpu|vidyalankar|university|college|institute\b',
            r'\ball\s*about\s*\w+.*exam\s*dates\b',
            r'\beligibility\s*,?\s*pattern\s*,?\s*syllabus\b',
            
            # Password reset notifications (not OTP generation)
            r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b',
            r'\breset\s*your\s*password\s*:\s*https?://\b',
            r'\bpassword\s*reset\s*link\b',
            
            # Registration alerts without OTP context
            r'\bregistration\s*is\s*initiated\s*for\b(?!.*otp\s*\d)',
            
            # Generic promotional patterns
            r'\bclick\s*here\s*to\s*(?:download|register|visit|learn)\b',
            r'\bvisit\s*:\s*https?://\b',
            r'\bfor\s*more\s*(?:info|information|details)\b.*https?://\b',
            r'\bshorturl\.at\b',
            r'\byoutu\.be\b',
            r'\bregards\s*,\s*\w+\b(?!.*otp)',  # Only exclude if no OTP context
        ]
        
        # Enhanced OTP patterns - More comprehensive and accurate
        self.true_otp_patterns = [
            # Direct OTP with numbers - Core patterns
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
            r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
            r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
            
            # Account-specific patterns
            r'\b(\d{4,8})\s*is\s*(?:the\s*)?(?:otp|one\s*time\s*password)\s*for\s*your\s*\w+\s*account\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
            
            # Platform-specific patterns
            r'\byour\s*otp\s*is\s*(\d{4,8})\s*id\s*:\s*\w+',  # Paytm style
            r'\b(\d{4,8})\s*is\s*your\s*one\s*time\s*password\s*to\s*proceed\s*on\s*\w+',
            
            # Service-specific OTP with numbers
            r'\bto\s*(?:proceed|login|register|verify)\s*.*one\s*time\s*password\s*(\d{4,8})\b',
            r'\bto\s*(?:register|login)\s*on\s*\w+\s*use\s*one\s*time\s*password\s*(\d{4,8})\b',
            
            # Connection conversion with OTP number
            r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\s*to\s*convert\s*connection\s*type\b',
            r'\bto\s*convert\s*connection\s*type.*one\s*time\s*password\s*\(otp\)\s*(\d{4,8})\b',
            
            # Time-sensitive OTP with numbers
            r'\b(\d{4,8}).*(?:valid\s*for|expires?\s*in)\s*\d+\s*(?:minutes?|mins?)\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*is\s*(\d{4,8}).*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
            
            # Security context patterns - Fixed to be more specific
            r'\b(?:otp|one\s*time\s*password)\s*(?:is\s*)?(\d{4,8}).*do\s*not\s*share.*(?:with\s*anyone|this\s*with\s*anyone)\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*is\s*(\d{4,8}).*do\s*not\s*share\b',
            
            # Never call/message patterns with OTP - More specific
            r'\b(\d{4,8}).*(?:never\s*call|never\s*message|will\s*never\s*call).*(?:asking\s*for\s*otp|you\s*asking\s*for\s*otp)\b',
            r'\bnever\s*calls\s*you\s*asking\s*for\s*otp.*(\d{4,8})\b',
            
            # Service/Platform context patterns
            r'\bsharing\s*(?:it|otp)\s*with\s*anyone\s*gives\s*them\s*full\s*access.*your\s*otp\s*is\s*(\d{4,8})\b',
        ]
        
        # Government/Identity service patterns
        self.government_patterns = [
            # Aadhaar comprehensive patterns
            r'\b(?:aadhaar|aadhar|adhaar|adhar|uid|uidai)\b(?!\s*(?:pay|payment|enabled))',
            r'\bunique\s*identification\b',
            r'\be[\-\s]?aadhaar\b',
            r'\bm[\-\s]?aadhaar\b',
            r'\baadhaar\s*(?:card|number|update|verification|linking|seeding|download|authentication)\b',
            r'\buid\s*(?:number|card|verification|authentication)\b',
            r'\baadhaar\s*verification\s*(?:is\s*)?pending\b',
            
            # Passport related
            r'\bpassport\b(?!\s*(?:size|photo))',
            r'\bpassbook\b',
            r'\bppt\s*(?:application|renewal|verification|status|tracking)\b',
            r'\bpassport\s*(?:application|renewal|verification|status|office|seva|kendra)\b',
            
            # PAN card patterns
            r'\bpan\s*(?:card|number|application|verification|correction|status)\b',
            r'\bpermanent\s*account\s*number\b',
            r'\bincome\s*tax\s*department.*pan\b',
            
            # Voter ID patterns
            r'\bvoter\s*(?:id|card|registration|verification|correction)\b',
            r'\belectoral\s*(?:roll|registration|photo\s*identity\s*card)\b',
            r'\bepic\s*(?:card|number)\b',
            
            # Driving License patterns
            r'\bdriving\s*(?:license|licence)\b',
            r'\bdl\s*(?:application|renewal|verification|test|status)\b',
            r'\brto\b.*(?:license|licence|dl)',
            
            # KYC and identity verification (but not in OTP context)
            r'\bkyc\s*(?:update|verification|pending|required|completed|documents|process)\b(?!.*otp\s*\d)',
            r'\bknow\s*your\s*customer\b',
            r'\bidentity\s*(?:verification|proof|document|card)\b',
            r'\bcomplete\s*your\s*kyc\s*process\b(?!.*otp)',
            
            # Government service portals
            r'\bdigilocker\b',
            r'\bumang\b',
            r'\bmygov\b',
            r'\birctc\b',
            r'\bcowin\b',
            
            # Official domains
            r'\bgov\.in\b',
            r'\bnic\.in\b',
            r'\buidai\.gov\.in\b',
        ]
        
        # Compile patterns for better performance
        self.compiled_banking_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.banking_exclusion_patterns]
        self.compiled_promotional_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.promotional_exclusion_patterns]
        self.compiled_true_otp_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.true_otp_patterns]
        self.compiled_gov_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.government_patterns]

    def clean_text(self, text: str) -> str:
        """Clean and normalize text for better matching"""
        if pd.isna(text):
            return ""
        
        # Convert to string and preserve important punctuation
        text = str(text).strip()
        
        # Remove extra whitespaces but preserve structure
        text = re.sub(r'\s+', ' ', text)
        
        return text

    def has_actual_otp_number(self, text: str) -> bool:
        """Check if text contains an actual OTP number (4-8 digits)"""
        # Look for 4-8 digit numbers in OTP context
        otp_number_patterns = [
            r'\b\d{4,8}\b.*\b(?:otp|one\s*time\s*password)\b',
            r'\b(?:otp|one\s*time\s*password)\b.*\b\d{4,8}\b',
        ]
        
        for pattern in otp_number_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def extract_otp_number(self, text: str) -> str:
        """Extract the OTP number from text if present"""
        # Look for patterns that capture the OTP number
        for pattern in self.compiled_true_otp_patterns:
            match = pattern.search(text)
            if match and match.groups():
                return match.group(1)
        
        # Alternative extraction for OTP numbers
        otp_extraction_patterns = [
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
        ]
        
        for pattern in otp_extraction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def is_strong_banking_context(self, text: str) -> bool:
        """Check for strong banking context that should override OTP classification"""
        text_lower = text.lower()
        
        # Very specific banking transaction patterns
        strong_banking_indicators = [
            'credited by rs', 'debited by rs', 'total bal:', 'clr bal:', 
            'available bal:', 'account balance:', 'a/c'
        ]
        
        # Check for transaction amounts
        if re.search(r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+', text_lower):
            return True
        
        # Check for balance statements
        if re.search(r'\b(?:total|clr|available)\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+', text_lower):
            return True
        
        # Check for account transaction patterns
        if re.search(r'\ba/c\s*\w+.*(?:credited|debited)', text_lower):
            return True
        
        # Bank specific warnings (but not generic OTP warnings)
        if 'emi postponement' in text_lower and 'never share otp' in text_lower:
            return True
        
        if 'card details/otp/cvv are secret' in text_lower:
            return True
        
        return False

    def is_promotional_message(self, text: str) -> bool:
        """Check if message is promotional/notification rather than OTP"""
        text_lower = text.lower()
        
        # Strong promotional indicators that should exclude even if OTP-like
        strong_promotional = [
            'data quota used', 'webinar:', 'tap to reset', 'registration is initiated',
            'exploring the field', 'exam dates, registration, eligibility'
        ]
        
        for indicator in strong_promotional:
            if indicator in text_lower:
                return True
        
        # Check for specific promotional patterns
        if re.search(r'\b\d+%\s*(?:daily\s*)?data\s*quota\s*used\b', text_lower):
            return True
        
        if re.search(r'\bwebinar\s*:.*(?:exploring|all\s*about)', text_lower):
            return True
        
        if re.search(r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b', text_lower):
            return True
        
        # Registration without OTP number context
        if re.search(r'\bregistration\s*is\s*initiated\s*for\b', text_lower) and not self.has_actual_otp_number(text):
            return True
        
        return False

    def has_strong_otp_indicators(self, text: str) -> bool:
        """Check for strong OTP-specific language patterns"""
        text_lower = text.lower()
        
        # Strong OTP-specific phrases
        strong_otp_phrases = [
            'is your otp', 'is the otp', 'otp is', 'one time password is',
            'your otp for', 'otp for your', 'to proceed on', 'otp to login',
            'otp to register', 'use one time password', 'your one time password'
        ]
        
        for phrase in strong_otp_phrases:
            if phrase in text_lower:
                return True
        
        return False

    def has_security_context(self, text: str) -> bool:
        """Check for OTP security warnings"""
        text_lower = text.lower()
        
        # Security context phrases specific to OTP
        security_phrases = [
            'do not share', 'never call', 'never message', 'will never call',
            'never calls you', 'keep your account safe', 'for security reasons',
            'gives them full access'
        ]
        
        # Must have security phrase AND OTP number
        has_security = any(phrase in text_lower for phrase in security_phrases)
        has_otp_num = self.has_actual_otp_number(text)
        
        return has_security and has_otp_num

    def has_validity_context(self, text: str) -> bool:
        """Check for OTP validity/expiry context"""
        text_lower = text.lower()
        
        validity_patterns = [
            r'\bvalid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
            r'\bexpires?\s*in\s*\d+\s*(?:minutes?|mins?)\b',
            r'\bis\s*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
        ]
        
        for pattern in validity_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def is_true_otp_message(self, text: str) -> bool:
        """Enhanced method to determine if this is a genuine OTP message"""
        
        # Must have actual OTP number
        if not self.has_actual_otp_number(text):
            return False
        
        # Check for strong OTP indicators
        if self.has_strong_otp_indicators(text):
            return True
        
        # Check for security context
        if self.has_security_context(text):
            return True
        
        # Check for validity context with OTP
        if self.has_validity_context(text) and 'otp' in text.lower():
            return True
        
        # Platform-specific patterns
        text_lower = text.lower()
        platforms = ['dream11', 'zupee', 'paytm', 'meesho', 'phonepe', 'ajio', 'jio']
        
        for platform in platforms:
            if platform in text_lower:
                # Check for account/login context
                if any(word in text_lower for word in ['account', 'login', 'register', 'proceed']):
                    return True
        
        return False

    def classify_message(self, message: str, sender_name: str = "") -> str:
        """Classify a single message with enhanced accuracy - FIXED VERSION"""
        
        # Clean both message and sender name
        clean_message = self.clean_text(message)
        clean_sender = self.clean_text(sender_name)
        
        # Combine message and sender for comprehensive analysis
        combined_text = f"{clean_message} {clean_sender}"
        
        # STEP 1: Quick check - Must have some key terms to continue
        text_lower = combined_text.lower()
        
        # STEP 2: Check for strong banking context FIRST (highest priority exclusion)
        if self.is_strong_banking_context(combined_text):
            return "Unknown"
        
        # STEP 3: Check for promotional content BEFORE other checks
        if self.is_promotional_message(combined_text):
            return "Unknown"
        
        # STEP 4: Apply banking exclusion patterns (very specific ones)
        for pattern in self.compiled_banking_exclusions:
            if pattern.search(combined_text):
                return "Unknown"
        
        # STEP 5: Apply promotional exclusion patterns
        for pattern in self.compiled_promotional_exclusions:
            if pattern.search(combined_text):
                return "Unknown"
        
        # STEP 6: Check for TRUE OTP messages (this is the main fix)
        # Use comprehensive OTP detection
        if self.is_true_otp_message(combined_text):
            return "Security & Authentication - OTP verification"
        
        # STEP 7: Check using pattern matching for OTP
        otp_pattern_matches = 0
        for pattern in self.compiled_true_otp_patterns:
            if pattern.search(combined_text):
                otp_pattern_matches += 1
        
        # If we have strong pattern matches AND actual OTP number, classify as OTP
        if otp_pattern_matches >= 1 and self.has_actual_otp_number(combined_text):
            return "Security & Authentication - OTP verification"
        
        # STEP 8: Check for government/identity services (after OTP check)
        gov_score = 0
        for pattern in self.compiled_gov_patterns:
            if pattern.search(combined_text):
                gov_score += 1
        
        if gov_score > 0:
            # If it has government context AND OTP number, it's an OTP for government service
            if self.has_actual_otp_number(combined_text):
                return "Security & Authentication - OTP verification"
            else:
                return "Government & Public Services - Identity services"
        
        # Default classification
        return "Unknown"

    def process_csv(self, file_path: str, output_path: str = None) -> pd.DataFrame:
        """Process the entire CSV file and add sector classification"""
        
        print("Loading CSV file...")
        start_time = time.time()
        
        # Read CSV with optimized settings for large files
        try:
            df = pd.read_csv(file_path, dtype=str, na_values=['', 'null', 'NULL', 'None'])
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return None
        
        print(f"Loaded {len(df):,} rows in {time.time() - start_time:.2f} seconds")
        
        # Check if required columns exist
        if 'message' not in df.columns:
            print("Error: 'message' column not found in CSV")
            return None
        
        # Create sender_name column if it doesn't exist
        if 'sender_name' not in df.columns:
            print("Warning: 'sender_name' column not found. Using empty values.")
            df['sender_name'] = ""
        
        # Keep only required columns
        existing_columns = ['message', 'sender_name']
        existing_columns = [col for col in existing_columns if col in df.columns]
        
        # Create new dataframe
        new_df = df[existing_columns].copy()
        
        if 'sender_name' not in new_df.columns:
            new_df['sender_name'] = ""
        
        # Add sector column at the beginning
        new_df.insert(0, 'sector', "")
        
        print("Starting classification...")
        classification_start = time.time()
        
        # Process in batches for memory efficiency and progress tracking
        batch_size = 5000  # Smaller batch for better progress updates
        total_rows = len(new_df)
        
        for i in range(0, total_rows, batch_size):
            end_idx = min(i + batch_size, total_rows)
            
            # Process batch
            for idx in range(i, end_idx):
                message = new_df.at[idx, 'message']
                sender = new_df.at[idx, 'sender_name'] if pd.notna(new_df.at[idx, 'sender_name']) else ""
                
                new_df.at[idx, 'sector'] = self.classify_message(message, sender)
            
            # Progress update
            progress = (end_idx / total_rows) * 100
            elapsed = time.time() - classification_start
            rate = end_idx / elapsed if elapsed > 0 else 0
            remaining_time = (total_rows - end_idx) / rate if rate > 0 else 0
            
            if (end_idx % 25000 == 0) or (end_idx == total_rows):
                print(f"Progress: {progress:.1f}% ({end_idx:,}/{total_rows:,}) | "
                      f"Rate: {rate:.0f} msgs/sec | ETA: {remaining_time/60:.1f} min")
        
        classification_time = time.time() - classification_start
        print(f"\nClassification completed in {classification_time/60:.1f} minutes")
        
        # Generate detailed classification summary
        print("\nClassification Summary:")
        print("=" * 60)
        sector_counts = new_df['sector'].value_counts()
        
        for sector, count in sector_counts.items():
            percentage = (count / len(new_df)) * 100
            print(f"{sector}: {count:,} ({percentage:.2f}%)")
        
        # Show specific counts for main categories
        otp_count = sector_counts.get('Security & Authentication - OTP verification', 0)
        gov_count = sector_counts.get('Government & Public Services - Identity services', 0)
        unknown_count = sector_counts.get('Unknown', 0)
        
        print(f"\nKey Statistics:")
        print(f"OTP Messages: {otp_count:,} ({(otp_count/total_rows)*100:.2f}%)")
        print(f"Government/Identity: {gov_count:,} ({(gov_count/total_rows)*100:.2f}%)")
        print(f"Unknown/Other: {unknown_count:,} ({(unknown_count/total_rows)*100:.2f}%)")
        
        # Save to output file
        if output_path is None:
            output_path = file_path.replace('.csv', '_classified.csv')
        
        print(f"\nSaving classified data to: {output_path}")
        save_start = time.time()
        
        try:
            new_df.to_csv(output_path, index=False, encoding='utf-8')
            print(f"File saved successfully in {time.time() - save_start:.2f} seconds")
        except Exception as e:
            print(f"Error saving file: {e}")
        
        return new_df

    def analyze_sample(self, df: pd.DataFrame, sector: str, n_samples: int = 5):
        """Analyze sample messages for a specific sector"""
        
        sector_messages = df[df['sector'] == sector]
        if len(sector_messages) == 0:
            print(f"No messages found for sector: {sector}")
            return
        
        print(f"\nSample messages for '{sector}':")
        print("=" * 80)
        
        sample = sector_messages.sample(n=min(n_samples, len(sector_messages)))
        
        for idx, row in sample.iterrows():
            message = str(row['message'])
            sender = str(row['sender_name']) if pd.notna(row['sender_name']) else "Unknown"
            
            # Show first 300 characters for better readability
            display_message = message[:300] + "..." if len(message) > 300 else message
            
            print(f"Sender: {sender}")
            print(f"Message: {display_message}")
            print("-" * 80)

    def test_messages(self):
        """Test the classifier with problematic example messages"""
        
        # Messages that should be classified as Unknown (promotional/notifications)
        unknown_messages = [
            "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517 For tips on how to manage data quota effectively, click https://youtu.be/ZFUDydctV78",
            "Webinar: Exploring the field of Psychology with an Honours degree On 2nd July, 5 PM. Regards, MIT-WPU. Register now: https://npfs.in/y0efch6KY",
            "Tap to reset your Instagram password: https://ig.me/1Ilu0lRRUpNTXOl",
            "Google Pay registration is initiated for ICICI Bank. If not done by you, report to your bank. Card details/OTP/CVV are SECRET. DO NOT disclose it to anyone.",
            "Vidyalankar Webinar: All About MAH BMS BBA CET Exam Dates, Registration, Eligibility, Pattern, Syllabus, & more. Attend on TOM-5Apr-6PM Reg shorturl.at/kpLTU",
            "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR Clr Bal: Rs. 47,695.00 CR. Never share OTP/Password for EMI postponement or any reason.-CBoI"
        ]
        
        # Messages that should be classified as OTP verification
        otp_messages = [
            "676653 is the OTP for your Dream11 account. Do not share this with anyone. Dream11 will never call or message asking for OTP.",
            "362835 is your OTP to login/register to your ZUPEE account. Do not share this with anyone. We will never call you asking for OTP. T&C apply Ref Id - iIiFwK30BUR",
            "Paytm never calls you asking for OTP. Sharing it with anyone gives them full access to your Paytm Account. Your OTP is 955980 ID: asasK/GTt2i",
            "Your OTP for Meesho login is 810671 and is valid for 30 mins. Please DO NOT share this OTP with anyone to keep your account safe. oBcOM6bXKNc Meesho",
            "41261 is your one time password to proceed on PhonePe AA. It is valid for 10 minutes. Do not share OTP with anyone. -PhonePe account aggregator",
            "805732 is the One Time Password (OTP) to convert connection type of your Jio Number 9399843517 from Prepaid to Postpaid. Order Number: NO0000VVGU46. This OTP is valid for 10 mins only.",
            "To Register on AJIO use One Time Password 4947 (valid for 10 mins). Make sure you do not share it with anyone for security reasons. iIRPCDc2lIh",
            "01717 is your one time password to proceed on PhonePe. It is valid for 10 minutes. Do not share your OTP with anyone. gZBmDyq76e3"
        ]
        
        # Messages that should be classified as Government services
        government_messages = [
            "Your Aadhaar verification is pending. Please complete your KYC process immediately.",
            "PAN card application status: Under process. Visit www.utiitsl.com for updates.",
            "Voter ID registration confirmation. Your Epic number will be sent via post."
        ]
        
        print("Testing Unknown/Promotional Messages:")
        print("=" * 80)
        
        correct_unknown = 0
        for i, message in enumerate(unknown_messages, 1):
            classification = self.classify_message(message)
            is_correct = classification == "Unknown"
            status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
            if is_correct:
                correct_unknown += 1
            
            print(f"Test {i}: {status}")
            print(f"Message: {message[:100]}...")
            print(f"Classification: {classification}")
            print("-" * 80)
        
        print(f"\nUnknown Messages Accuracy: {correct_unknown}/{len(unknown_messages)} ({(correct_unknown/len(unknown_messages)*100):.1f}%)")
        
        print("\nTesting OTP Verification Messages:")
        print("=" * 80)
        
        correct_otp = 0
        for i, message in enumerate(otp_messages, 1):
            classification = self.classify_message(message)
            is_correct = classification == "Security & Authentication - OTP verification"
            status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
            if is_correct:
                correct_otp += 1
            
            print(f"Test {i}: {status}")
            print(f"Message: {message[:100]}...")
            print(f"Classification: {classification}")
            
            # Debug failed classifications
            if not is_correct:
                print(f"  -> DEBUG: Has OTP Number: {self.has_actual_otp_number(message)}")
                print(f"  -> DEBUG: Strong OTP Indicators: {self.has_strong_otp_indicators(message)}")
                print(f"  -> DEBUG: Security Context: {self.has_security_context(message)}")
                print(f"  -> DEBUG: Is True OTP: {self.is_true_otp_message(message)}")
            
            print("-" * 80)
        
        print(f"\nOTP Messages Accuracy: {correct_otp}/{len(otp_messages)} ({(correct_otp/len(otp_messages)*100):.1f}%)")
        
        print("\nTesting Government Service Messages:")
        print("=" * 80)
        
        correct_gov = 0
        for i, message in enumerate(government_messages, 1):
            classification = self.classify_message(message)
            is_correct = classification == "Government & Public Services - Identity services"
            status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
            if is_correct:
                correct_gov += 1
            
            print(f"Test {i}: {status}")
            print(f"Message: {message[:100]}...")
            print(f"Classification: {classification}")
            print("-" * 80)
        
        total_correct = correct_unknown + correct_otp + correct_gov
        total_messages = len(unknown_messages) + len(otp_messages) + len(government_messages)
        
        print(f"\nGovernment Messages Accuracy: {correct_gov}/{len(government_messages)} ({(correct_gov/len(government_messages)*100):.1f}%)")
        print(f"\nOverall Test Accuracy: {total_correct}/{total_messages} ({(total_correct/total_messages)*100:.1f}%)")

    def debug_classification(self, message: str, sender_name: str = ""):
        """Debug function to show step-by-step classification process"""
        clean_message = self.clean_text(message)
        clean_sender = self.clean_text(sender_name)
        combined_text = f"{clean_message} {clean_sender}"
        
        print(f"Debug Classification for: {message[:100]}...")
        print("=" * 60)
        
        # Step 1: Banking context check
        banking_context = self.is_strong_banking_context(combined_text)
        print(f"1. Strong Banking Context: {banking_context}")
        
        if banking_context:
            print("   → Classified as Unknown (Strong Banking context)")
            return "Unknown"
        
        # Step 2: Promotional check
        promotional = self.is_promotional_message(combined_text)
        print(f"2. Promotional Message: {promotional}")
        
        if promotional:
            print("   → Classified as Unknown (Promotional)")
            return "Unknown"
        
        # Step 3: Exclusion patterns
        banking_exclusion_match = any(pattern.search(combined_text) for pattern in self.compiled_banking_exclusions)
        promo_exclusion_match = any(pattern.search(combined_text) for pattern in self.compiled_promotional_exclusions)
        print(f"3. Banking Exclusion Pattern: {banking_exclusion_match}")
        print(f"4. Promotional Exclusion Pattern: {promo_exclusion_match}")
        
        if banking_exclusion_match or promo_exclusion_match:
            print("   → Classified as Unknown (Exclusion pattern matched)")
            return "Unknown"
        
        # Step 5: OTP analysis (before government)
        has_otp_num = self.has_actual_otp_number(combined_text)
        is_true_otp = self.is_true_otp_message(combined_text)
        otp_pattern_matches = sum(1 for pattern in self.compiled_true_otp_patterns if pattern.search(combined_text))
        
        print(f"5. Has Actual OTP Number: {has_otp_num}")
        print(f"6. Is True OTP Message: {is_true_otp}")
        print(f"7. OTP Pattern Matches: {otp_pattern_matches}")
        print(f"8. Strong OTP Indicators: {self.has_strong_otp_indicators(combined_text)}")
        print(f"9. Security Context: {self.has_security_context(combined_text)}")
        print(f"10. Validity Context: {self.has_validity_context(combined_text)}")
        
        if is_true_otp or (otp_pattern_matches >= 1 and has_otp_num):
            print("   → Classified as OTP verification")
            return "Security & Authentication - OTP verification"
        
        # Step 6: Government patterns
        gov_matches = sum(1 for pattern in self.compiled_gov_patterns if pattern.search(combined_text))
        print(f"11. Government Pattern Matches: {gov_matches}")
        
        # Final classification logic
        if gov_matches > 0:
            if has_otp_num:
                print("   → Classified as OTP verification (Government OTP)")
                return "Security & Authentication - OTP verification"
            else:
                print("   → Classified as Government & Public Services")
                return "Government & Public Services - Identity services"
        else:
            print("   → Classified as Unknown")
            return "Unknown"

    def analyze_misclassifications(self, df: pd.DataFrame):
        """Analyze potential misclassifications in the dataset"""
        print("\nAnalyzing Potential Misclassifications:")
        print("=" * 60)
        
        # Check for messages with 'otp' that are classified as Unknown
        otp_unknown = df[(df['message'].str.contains('otp|OTP', case=False, na=False)) & 
                        (df['sector'] == 'Unknown')]
        
        print(f"Messages containing 'OTP' classified as Unknown: {len(otp_unknown)}")
        
        if len(otp_unknown) > 0:
            print("Sample messages:")
            for i, (_, row) in enumerate(otp_unknown.head(3).iterrows()):
                print(f"  {i+1}. {row['message'][:150]}...")
        
        # Check for messages without numbers classified as OTP
        otp_messages = df[df['sector'] == 'Security & Authentication - OTP verification']
        otp_without_numbers = otp_messages[~otp_messages['message'].str.contains(r'\d{4,8}', na=False)]
        
        print(f"\nOTP messages without 4-8 digit numbers: {len(otp_without_numbers)}")
        
        if len(otp_without_numbers) > 0:
            print("Sample messages:")
            for i, (_, row) in enumerate(otp_without_numbers.head(3).iterrows()):
                print(f"  {i+1}. {row['message'][:150]}...")


def main():
    # Initialize classifier
    classifier = SMSClassifier()
    
    print("Enhanced SMS Classifier with Improved Accuracy - FIXED VERSION")
    print("=" * 60)
    
    # Test the example messages first
    classifier.test_messages()
    
    # Ask for debug mode
    debug_mode = input("\nWould you like to test debug mode on specific messages? (y/n): ").lower().strip()
    
    if debug_mode == 'y':
        test_msg = input("Enter a message to debug: ").strip()
        if test_msg:
            classifier.debug_classification(test_msg)
    
    # Ask if user wants to process a CSV file
    process_csv = input(f"\nWould you like to process a CSV file? (y/n): ").lower().strip()
    
    if process_csv == 'y':
        # Specify your CSV file path
        input_file = input("Enter the path to your CSV file: ").strip().strip('"')
        
        if not input_file:
            print("No file path provided. Exiting.")
            return
        
        # Ask for output file path
        output_file = input("Enter output file path (or press Enter for auto-naming): ").strip().strip('"')
        if not output_file:
            output_file = None
        
        # Process the CSV file
        print(f"\nProcessing file: {input_file}")
        print("Processing 26 lakh records...")
        print("Estimated time: 30-45 minutes")
        print("The classifier uses enhanced patterns for better accuracy.")
        
        result_df = classifier.process_csv(input_file, output_file)
        
        if result_df is not None:
            print("\nClassification completed successfully!")
            
            # Analyze potential misclassifications
            classifier.analyze_misclassifications(result_df)
            
            # Ask if user wants to see sample messages
            show_samples = input("\nWould you like to see sample classified messages? (y/n): ").lower().strip()
            
            if show_samples == 'y':
                # Show samples for each category
                sectors = result_df['sector'].unique()
                for sector in sectors:
                    if len(result_df[result_df['sector'] == sector]) > 0:
                        classifier.analyze_sample(result_df, sector, 3)
            
            print(f"\n🎉 Process completed successfully!")
            print(f"📁 Output file: {output_file if output_file else input_file.replace('.csv', '_classified.csv')}")
        else:
            print("Classification failed. Please check your file path and format.")


if __name__ == "__main__":
    main()
    