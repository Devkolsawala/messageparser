import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import time
from difflib import SequenceMatcher

class EnhancedOTPMessageParser:
    def __init__(self):
        # OTP extraction patterns (capture groups for the actual OTP number)
        self.otp_patterns = [
            # New patterns for messages like "<#> Your One-Time Password(OTP) for UTS Mobile Ticket is 3614..."
            r'\b(?:one[- ]?time[- ]?password|otp)\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
            r'<#>\s*your\s*one[- ]?time[- ]?password\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
            
            # Existing patterns
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
            r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
            r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*(?:the\s*)?(?:otp|one\s*time\s*password)\s*for\s*your\s*\w+\s*account\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
            r'\b(\d{4,8})\s*is\s*your\s*one\s*time\s*password\s*to\s*proceed\s*on\s*\w+',
            r'\byour\s*otp\s*is\s*(\d{4,8})\s*id\s*:\s*\w+',  # Paytm style
            r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\b',
            r'\bto\s*(?:proceed|login|register|verify)\s*.*one\s*time\s*password\s*(\d{4,8})\b',
            r'\bto\s*(?:register|login)\s*on\s*\w+\s*use\s*one\s*time\s*password\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\s*to\s*convert\s*connection\s*type\b',
        ]
        
        # Enhanced OTP classification patterns from classifier
        self.true_otp_patterns = [
            # New patterns
            r'\b(?:one[- ]?time[- ]?password|otp)\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
            r'<#>\s*your\s*one[- ]?time[- ]?password\s*\(?otp\)?\s*for\s*.*?\s*is\s*(\d{4,8})\b',
            
            # Existing patterns
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
            r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
            r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
            r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*(?:the\s*)?(?:otp|one\s*time\s*password)\s*for\s*your\s*\w+\s*account\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
            r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
            r'\byour\s*otp\s*is\s*(\d{4,8})\s*id\s*:\s*\w+',
            r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\b',
            r'\bto\s*(?:proceed|login|register|verify)\s*.*one\s*time\s*password\s*(\d{4,8})\b',
            r'\bsharing\s*(?:it|otp)\s*with\s*anyone\s*gives\s*them\s*full\s*access.*your\s*otp\s*is\s*(\d{4,8})\b',
            r'\b(\d{4,8}).*(?:valid\s*for|expires?\s*in)\s*\d+\s*(?:minutes?|mins?)\b',
            r'\byour\s*(?:otp|one\s*time\s*password)\s*is\s*(\d{4,8}).*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
        ]
        
        # Banking/Transaction exclusion patterns (should NOT be classified as OTP)
        self.banking_exclusion_patterns = [
            r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+',
            r'\btotal\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
            r'\bclr\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
            r'\bavailable\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
            r'\ba/c\s*\d+.*(?:credited|debited).*rs\.?\s*[\d,]+',
            r'\bnever\s*share\s*otp.*(?:emi\s*postponement|any\s*reason).*-\w+$',
            r'\bcard\s*details/otp/cvv\s*are\s*secret',
            r'\bif\s*not\s*done\s*by\s*you.*report.*bank',
        ]
        
        # Promotional/Notification exclusion patterns
        self.promotional_exclusion_patterns = [
            r'\b\d+%\s*daily\s*data\s*quota\s*used\b',
            r'\bdata\s*quota\s*(?:used|consumed|remaining)\b',
            r'\binternet\s*speed\s*will\s*be\s*reduced\b',
            r'\bto\s*continue\s*enjoying\s*high\s*speed\s*internet\b',
            r'\bclick\s*https?://\w+.*recharge\b',
            r'\bwebinar\s*:\s*(?:exploring|all\s*about)',
            r'\b(?:register|attend)\s*(?:now|on)\s*.*https?://\b',
            r'\bmit-wpu|vidyalankar|university|college|institute\b',
            r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b',
            r'\breset\s*your\s*password\s*:\s*https?://\b',
            r'\bregistration\s*is\s*initiated\s*for\b(?!.*otp\s*\d)',
        ]
        
        # Expiry/validity patterns
        self.expiry_patterns = [
            r'\bvalid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bexpires?\s*in\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bis\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bonly\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bvalidity\s*:\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bthis\s*otp\s*is\s*valid\s*for\s*(\d+)\s*(minutes?|mins?|min)\b',
        ]
        
        # Company/Service name patterns with fuzzy matching support
        self.company_patterns = {
            'UTS Mobile Ticket': [r'\buts\s*mobile\s*ticket\b', r'\buts\b'],
            'CRIS': [r'\bcris\b'],
            'Dream11': [r'\bdream11\b', r'\bdream\s*11\b'],
            'Paytm': [r'\bpaytm\b'],
            'PhonePe': [r'\bphonepe\b', r'\bphone\s*pe\b'],
            'Zupee': [r'\bzupee\b'],
            'Meesho': [r'\bmeesho\b'],
            'AJIO': [r'\bajio\b'],
            'Google Pay': [r'\bgoogle\s*pay\b', r'\bgpay\b'],
            'Amazon': [r'\bamazon\b'],
            'Flipkart': [r'\bflipkart\b'],
            'Myntra': [r'\bmyntra\b'],
            'Swiggy': [r'\bswiggy\b'],
            'Zomato': [r'\bzomato\b'],
            'Ola': [r'\bola\b(?!\s*(?:money|electric))'],
            'Uber': [r'\buber\b'],
            'BigBasket': [r'\bbigbasket\b', r'\bbig\s*basket\b'],
            'BookMyShow': [r'\bbookmyshow\b', r'\bbook\s*my\s*show\b'],
            'MakeMyTrip': [r'\bmakemytrip\b', r'\bmake\s*my\s*trip\b'],
            'ICICI Bank': [r'\bicici\b'],
            'HDFC': [r'\bhdfc\b'],
            'SBI': [r'\bsbi\b', r'\bstate\s*bank\s*of\s*india\b'],
            'Axis Bank': [r'\baxis\s*bank\b'],
            'Jio': [r'\bjio\b'],
            'Airtel': [r'\bairtel\b'],
            'Vi': [r'\bvi\b(?:\s|$)', r'\bvodafone\s*idea\b'],
            'WhatsApp': [r'\bwhatsapp\b', r'\bwhats\s*app\b'],
            'Facebook': [r'\bfacebook\b'],
            'Instagram': [r'\binstagram\b'],
        }
        
        # Purpose/Action patterns
        self.purpose_patterns = {
            'Login': [r'\bto\s*(?:login|log\s*in|sign\s*in)\b', r'\bfor\s*(?:login|log\s*in|sign\s*in)\b'],
            'Registration': [r'\bto\s*(?:register|registration|sign\s*up)\b', r'\bfor\s*(?:registration|sign\s*up)\b'],
            'Verification': [r'\bto\s*(?:verify|verification)\b', r'\bfor\s*(?:verification|account\s*verification)\b'],
            'Proceed': [r'\bto\s*proceed\b'],
            'Reset Password': [r'\bto\s*reset\s*(?:password|pin)\b', r'\bpassword\s*reset\b'],
            'Transaction': [r'\bto\s*(?:complete|authorize)\s*(?:transaction|payment)\b'],
            'Convert': [r'\bto\s*convert\s*connection\s*type\b'],
            'Mobile Ticket': [r'for\s*uts\s*mobile\s*ticket'], # New purpose
        }
        
        # Security warning patterns
        self.security_patterns = [
            r'\bdo\s*not\s*share\b',
            r'\bnever\s*share\b', 
            r'\bnever\s*call\b',
            r'\bnever\s*message\b',
            r'\bwill\s*never\s*call\b',
            r'\bkeep\s*your\s*account\s*safe\b',
            r'\bfor\s*security\s*reasons\b',
            r'\bgives\s*them\s*full\s*access\b',
        ]
        
        # Compile all patterns for better performance
        self.compiled_otp_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.otp_patterns]
        self.compiled_true_otp_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.true_otp_patterns]
        self.compiled_banking_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.banking_exclusion_patterns]
        self.compiled_promotional_exclusions = [re.compile(pattern, re.IGNORECASE) for pattern in self.promotional_exclusion_patterns]
        self.compiled_expiry_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.expiry_patterns]
        self.compiled_security_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.security_patterns]
        
        # Compile company patterns
        self.compiled_company_patterns = {}
        for company, patterns in self.company_patterns.items():
            self.compiled_company_patterns[company] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        # Compile purpose patterns
        self.compiled_purpose_patterns = {}
        for purpose, patterns in self.purpose_patterns.items():
            self.compiled_purpose_patterns[purpose] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def clean_text(self, text: str) -> str:
        """Clean and normalize text for better matching"""
        if pd.isna(text):
            return ""
        
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def has_actual_otp_number(self, text: str) -> bool:
        """Check if text contains an actual OTP number (4-8 digits)"""
        otp_number_patterns = [
            r'\b\d{4,8}\b.*\b(?:otp|one\s*time\s*password)\b',
            r'\b(?:otp|one\s*time\s*password)\b.*\b\d{4,8}\b',
        ]
        
        for pattern in otp_number_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def has_strong_otp_indicators(self, text: str) -> bool:
        """Check for strong OTP-specific language patterns"""
        text_lower = text.lower()
        
        strong_otp_phrases = [
            'is your otp', 'is the otp', 'otp is', 'one time password is',
            'your otp for', 'otp for your', 'to proceed on', 'otp to login',
            'otp to register', 'use one time password', 'your one time password'
        ]
        
        return any(phrase in text_lower for phrase in strong_otp_phrases)

    def has_security_context(self, text: str) -> bool:
        """Check for OTP security warnings"""
        text_lower = text.lower()
        
        security_phrases = [
            'do not share', 'never call', 'never message', 'will never call',
            'never calls you', 'keep your account safe', 'for security reasons',
            'gives them full access'
        ]
        
        has_security = any(phrase in text_lower for phrase in security_phrases)
        has_otp_num = self.has_actual_otp_number(text)
        
        return has_security and has_otp_num

    def has_validity_context(self, text: str) -> bool:
        """Check for OTP validity/expiry context"""
        validity_patterns = [
            r'\bvalid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
            r'\bexpires?\s*in\s*\d+\s*(?:minutes?|mins?)\b',
            r'\bis\s*valid\s*for\s*\d+\s*(?:minutes?|mins?)\b',
        ]
        
        for pattern in validity_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def is_strong_banking_context(self, text: str) -> bool:
        """Check for strong banking context that should exclude OTP classification"""
        text_lower = text.lower()
        
        if re.search(r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+', text_lower):
            return True
        if re.search(r'\b(?:total|clr|available)\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+', text_lower):
            return True
        if re.search(r'\ba/c\s*\w+.*(?:credited|debited)', text_lower):
            return True
        if 'emi postponement' in text_lower and 'never share otp' in text_lower:
            return True
        if 'card details/otp/cvv are secret' in text_lower:
            return True
        
        return False

    def is_promotional_message(self, text: str) -> bool:
        """Check if message is promotional/notification rather than OTP"""
        text_lower = text.lower()
        
        strong_promotional = [
            'data quota used', 'webinar:', 'tap to reset', 'registration is initiated',
            'exploring the field', 'exam dates, registration, eligibility'
        ]
        
        for indicator in strong_promotional:
            if indicator in text_lower:
                return True
        
        if re.search(r'\b\d+%\s*(?:daily\s*)?data\s*quota\s*used\b', text_lower):
            return True
        if re.search(r'\bwebinar\s*:.*(?:exploring|all\s*about)', text_lower):
            return True
        if re.search(r'\btap\s*to\s*reset\s*your\s*\w+\s*password\b', text_lower):
            return True
        if re.search(r'\bregistration\s*is\s*initiated\s*for\b', text_lower) and not self.has_actual_otp_number(text):
            return True
        
        return False

    def is_true_otp_message(self, text: str) -> bool:
        """Enhanced method to determine if this is a genuine OTP message"""
        
        # Must have actual OTP number
        if not self.has_actual_otp_number(text):
            return False
        
        # Check for strong banking context first (exclusion)
        if self.is_strong_banking_context(text):
            return False
        
        # Check for promotional content (exclusion)
        if self.is_promotional_message(text):
            return False
        
        # Apply exclusion patterns
        for pattern in self.compiled_banking_exclusions:
            if pattern.search(text):
                return False
        
        for pattern in self.compiled_promotional_exclusions:
            if pattern.search(text):
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
        platforms = ['dream11', 'zupee', 'paytm', 'meesho', 'phonepe', 'ajio', 'jio', 'uts']
        
        for platform in platforms:
            if platform in text_lower:
                if any(word in text_lower for word in ['account', 'login', 'register', 'proceed', 'ticket']):
                    return True
        
        # Check true OTP patterns
        otp_pattern_matches = sum(1 for pattern in self.compiled_true_otp_patterns if pattern.search(text))
        if otp_pattern_matches >= 1:
            return True
        
        return False

    def fuzzy_match_company(self, text: str, threshold: float = 0.8) -> Optional[str]:
        """Use fuzzy matching to identify company names"""
        text_words = re.findall(r'\b\w+\b', text.lower())
        
        for company in self.company_patterns.keys():
            company_lower = company.lower()
            
            # Direct fuzzy matching
            for word in text_words:
                ratio = SequenceMatcher(None, word, company_lower).ratio()
                if ratio >= threshold:
                    return company
            
            # Check for partial matches in company name
            for part in company_lower.split():
                if len(part) >= 3:  # Only check meaningful parts
                    for word in text_words:
                        if len(word) >= 3:
                            ratio = SequenceMatcher(None, word, part).ratio()
                            if ratio >= threshold:
                                return company
        
        return None

    def extract_otp_code(self, text: str) -> Optional[str]:
        """Extract OTP code from message with enhanced patterns"""
        if pd.isna(text):
            return None
        
        text = str(text).strip()
        
        # Try each OTP pattern
        for pattern in self.compiled_otp_patterns:
            match = pattern.search(text)
            if match and match.groups():
                return match.group(1)
        
        # Fallback patterns
        fallback_patterns = [
            r'\b(\d{4,8})\b.*(?:otp|one\s*time\s*password)',
            r'(?:otp|one\s*time\s*password).*\b(\d{4,8})\b',
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
        """Extract expiry time information"""
        if pd.isna(text):
            return None
        
        text = str(text).strip()
        
        for pattern in self.compiled_expiry_patterns:
            match = pattern.search(text)
            if match:
                return {
                    'duration': match.group(1),
                    'unit': match.group(2),
                    'full_text': match.group(0)
                }
        
        return None

    def extract_company_name(self, text: str, sender_name: str = "") -> Optional[str]:
        """Extract company/service name with regex and fuzzy matching"""
        if pd.isna(text):
            text = ""
        if pd.isna(sender_name):
            sender_name = ""
        
        combined_text = f"{str(text)} {str(sender_name)}"
        
        # First try exact regex patterns
        for company, patterns in self.compiled_company_patterns.items():
            for pattern in patterns:
                if pattern.search(combined_text):
                    return company
        
        # Try fuzzy matching
        fuzzy_company = self.fuzzy_match_company(combined_text)
        if fuzzy_company:
            return fuzzy_company
        
        # Extract from sender patterns
        sender_patterns = [
            r'([A-Z][A-Za-z]+)(?:-|\s|$)',
            r'([A-Z]{2,})',
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, sender_name)
            if match and len(match.group(1)) >= 2:
                return match.group(1)
        
        return None

    def extract_purpose(self, text: str) -> Optional[str]:
        """Extract the purpose of the OTP"""
        if pd.isna(text):
            return None
        
        text = str(text).strip()
        
        for purpose, patterns in self.compiled_purpose_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return purpose
        
        return None

    def extract_security_warnings(self, text: str) -> List[str]:
        """Extract security warning messages"""
        if pd.isna(text):
            return []
        
        text = str(text).strip()
        warnings = []
        
        for pattern in self.compiled_security_patterns:
            match = pattern.search(text)
            if match:
                warnings.append(match.group(0))
        
        return warnings

    def extract_reference_id(self, text: str) -> Optional[str]:
        """Extract reference ID, transaction ID, or order number"""
        if pd.isna(text):
            return None
        
        text = str(text).strip()
        
        ref_patterns = [
            r'\bid\s*:\s*([A-Za-z0-9/_]+)',
            r'\bref\s*(?:id|no|number)\s*[:|-]\s*([A-Za-z0-9/_]+)',
            r'\border\s*(?:number|no)\s*:\s*([A-Za-z0-9]+)',
            r'\btxn\s*(?:id|no)\s*:\s*([A-Za-z0-9]+)',
            r'\btransaction\s*(?:id|no)\s*:\s*([A-Za-z0-9]+)',
            r'\breference\s*:\s*([A-Za-z0-9]+)',
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ref_id = match.group(1).strip()
                if 3 <= len(ref_id) <= 20:
                    return ref_id
        
        return None

    def extract_phone_number(self, text: str) -> Optional[str]:
        """Extract phone number if mentioned in the message"""
        if pd.isna(text):
            return None
        
        text = str(text).strip()
        
        phone_patterns = [
            r'\bjio\s*number\s*:\s*(\d{10})\b',
            r'\bmobile\s*(?:number|no)\s*:\s*(\d{10})\b',
            r'\bphone\s*(?:number|no)\s*:\s*(\d{10})\b',
            r'\bnumber\s*(\d{10})\b',
            r'\b(\d{10})\b(?=\s*(?:from|for|$))',
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def extract_sender_info(self, sender_name: str) -> Dict[str, str]:
        """Extract information from sender name/ID"""
        if pd.isna(sender_name):
            return {'sender_type': None, 'sender_clean': None}
        
        sender_clean = str(sender_name).strip()
        
        # Determine sender type
        if re.match(r'^[A-Z]{2}-', sender_clean):
            sender_type = "Short Code"
        elif re.match(r'^[A-Z]+$', sender_clean):
            sender_type = "Alpha Code"
        elif re.match(r'^\d+$', sender_clean):
            sender_type = "Numeric"
        else:
            sender_type = "Mixed"
        
        return {
            'sender_type': sender_type,
            'sender_clean': sender_clean
        }

    def calculate_otp_confidence_score(self, text: str, sender_name: str = "") -> float:
        """Calculate confidence score for OTP classification"""
        combined_text = f"{text} {sender_name}"
        score = 0.0
        
        # Base OTP indicators (40 points)
        if self.has_actual_otp_number(combined_text):
            score += 40
        
        # Strong OTP language (30 points)
        if self.has_strong_otp_indicators(combined_text):
            score += 30
        
        # Security context (20 points)
        if self.has_security_context(combined_text):
            score += 20
        
        # Validity context (10 points)
        if self.has_validity_context(combined_text):
            score += 10
        
        # Pattern matching bonus
        pattern_matches = sum(1 for pattern in self.compiled_true_otp_patterns if pattern.search(combined_text))
        score += min(pattern_matches * 5, 20)  # Max 20 bonus points
        
        # Penalties for exclusions
        if self.is_strong_banking_context(combined_text):
            score -= 50
        
        if self.is_promotional_message(combined_text):
            score -= 30
        
        return max(0, min(100, score))  # Ensure score is between 0-100

    def parse_single_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse a single message and extract all relevant information"""
        
        # Clean inputs
        clean_message = self.clean_text(message)
        clean_sender = self.clean_text(sender_name)
        combined_text = f"{clean_message} {clean_sender}"
        
        # Calculate confidence score
        confidence_score = self.calculate_otp_confidence_score(clean_message, clean_sender)
        
        # Determine if this is an OTP message (threshold: 50)
        is_otp_message = confidence_score >= 50 and self.is_true_otp_message(combined_text)
        
        if not is_otp_message:
            return {
                'status': 'rejected',
                'reason': 'Message not related to Security & Authentication - OTP verification',
                'confidence_score': confidence_score,
                'message_preview': clean_message[:100] + "..." if len(clean_message) > 100 else clean_message
            }
        
        # Extract sender information
        sender_info = self.extract_sender_info(sender_name)
        
        # Parse OTP information
        result = {
            'status': 'parsed',
            'confidence_score': confidence_score,
            'otp_code': self.extract_otp_code(clean_message),
            'company_name': self.extract_company_name(clean_message, clean_sender),
            'purpose': self.extract_purpose(clean_message),
            'expiry_info': self.extract_expiry_time(clean_message),
            'security_warnings': self.extract_security_warnings(clean_message),
            'reference_id': self.extract_reference_id(clean_message),
            'phone_number': self.extract_phone_number(clean_message),
            'sender_name': clean_sender if clean_sender else None,
            'sender_type': sender_info['sender_type'],
            'sender_clean': sender_info['sender_clean'],
            'raw_message': clean_message,
            'message_length': len(clean_message),
            'contains_url': bool(re.search(r'https?://\S+', clean_message)),
        }
        
        # Format expiry info for better display
        if result['expiry_info']:
            result['expiry_duration'] = f"{result['expiry_info']['duration']} {result['expiry_info']['unit']}"
            result['expiry_full_text'] = result['expiry_info']['full_text']
        else:
            result['expiry_duration'] = None
            result['expiry_full_text'] = None
        
        # Convert security warnings list to string
        if result['security_warnings']:
            result['security_warnings_text'] = "; ".join(result['security_warnings'])
        else:
            result['security_warnings_text'] = None
        
        return result

    def process_csv_file(self, input_file: str, output_file: str = None) -> Dict:
        """Process CSV file and extract OTP information from messages"""
        
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
        
        # Check required columns
        if 'message' not in df.columns:
            print("Error: 'message' column not found")
            return None
        
        # Ensure sender_name column exists
        if 'sender_name' not in df.columns:
            print("Warning: 'sender_name' column not found. Using empty values.")
            df['sender_name'] = ""
        
        print(f"Analyzing {len(df):,} messages for OTP content...")
        
        # Initialize results
        otp_messages = []
        rejected_messages = []
        
        print("Starting message analysis...")
        parse_start = time.time()
        
        # Process messages in batches
        batch_size = 1000
        total_messages = len(df)
        
        for i in range(0, total_messages, batch_size):
            end_idx = min(i + batch_size, total_messages)
            
            # Process batch
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
            
            # Progress update
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
        
        # Generate comprehensive results
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'otp_messages_found': len(otp_messages),
                'rejected_messages': len(rejected_messages),
                'otp_detection_rate': round((len(otp_messages) / total_messages) * 100, 2),
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '2.1_enhanced' # Version updated
            },
            'summary_statistics': self.generate_summary_stats(otp_messages),
            'otp_messages': otp_messages,
            'sample_rejected_messages': rejected_messages[:10]  # Include sample of rejected messages
        }
        
        # Display summary
        self.display_parsing_summary(results)
        
        # Save results
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
        """Generate comprehensive summary statistics"""
        
        if not otp_messages:
            return {}
        
        total_otp = len(otp_messages)
        
        # Extract statistics
        otp_codes_found = sum(1 for msg in otp_messages if msg.get('otp_code'))
        companies_identified = sum(1 for msg in otp_messages if msg.get('company_name'))
        purposes_identified = sum(1 for msg in otp_messages if msg.get('purpose'))
        expiry_found = sum(1 for msg in otp_messages if msg.get('expiry_info'))
        security_warnings = sum(1 for msg in otp_messages if msg.get('security_warnings'))
        reference_ids = sum(1 for msg in otp_messages if msg.get('reference_id'))
        phone_numbers = sum(1 for msg in otp_messages if msg.get('phone_number'))
        
        # Company distribution
        companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
        company_counts = {}
        for company in companies:
            company_counts[company] = company_counts.get(company, 0) + 1
        
        # Purpose distribution
        purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
        purpose_counts = {}
        for purpose in purposes:
            purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        
        # Expiry distribution
        expiry_durations = [msg.get('expiry_duration') for msg in otp_messages if msg.get('expiry_duration')]
        expiry_counts = {}
        for duration in expiry_durations:
            expiry_counts[duration] = expiry_counts.get(duration, 0) + 1
        
        # Confidence score distribution
        confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            'extraction_rates': {
                'otp_codes_extracted': round((otp_codes_found / total_otp) * 100, 2),
                'companies_identified': round((companies_identified / total_otp) * 100, 2),
                'purposes_identified': round((purposes_identified / total_otp) * 100, 2),
                'expiry_info_found': round((expiry_found / total_otp) * 100, 2),
                'security_warnings_found': round((security_warnings / total_otp) * 100, 2),
                'reference_ids_found': round((reference_ids / total_otp) * 100, 2),
                'phone_numbers_found': round((phone_numbers / total_otp) * 100, 2),
            },
            'distributions': {
                'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
                'expiry_durations': dict(sorted(expiry_counts.items(), key=lambda x: x[1], reverse=True)),
            },
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
                'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
                'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
            }
        }

    def display_parsing_summary(self, results: Dict):
        """Display comprehensive parsing summary"""
        
        metadata = results['metadata']
        stats = results.get('summary_statistics', {})
        
        print("\n" + "="*80)
        print("OTP PARSING RESULTS SUMMARY")
        print("="*80)
        
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"Messages Rejected: {metadata['rejected_messages']:,}")
        print(f"OTP Detection Rate: {metadata['otp_detection_rate']}%")
        print(f"Processing Time: {metadata['processing_time_minutes']} minutes")
        
        if not stats:
            print("\nNo OTP messages found to analyze.")
            return
        
        extraction_rates = stats.get('extraction_rates', {})
        distributions = stats.get('distributions', {})
        quality_metrics = stats.get('quality_metrics', {})
        
        print("\n" + "="*60)
        print("EXTRACTION ACCURACY")
        print("="*60)
        
        for metric, rate in extraction_rates.items():
            print(f"{metric.replace('_', ' ').title()}: {rate}%")
        
        print("\n" + "="*60)
        print("TOP COMPANIES/SERVICES")
        print("="*60)
        
        for company, count in list(distributions.get('top_companies', {}).items())[:10]:
            percentage = (count / metadata['otp_messages_found']) * 100
            print(f"{company}: {count:,} ({percentage:.1f}%)")
        
        print("\n" + "="*60)
        print("PURPOSE DISTRIBUTION")
        print("="*60)
        
        for purpose, count in distributions.get('purposes', {}).items():
            percentage = (count / metadata['otp_messages_found']) * 100
            print(f"{purpose}: {count:,} ({percentage:.1f}%)")
        
        print("\n" + "="*60)
        print("QUALITY METRICS")
        print("="*60)
        
        print(f"Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")
        print(f"High Confidence (≥80): {quality_metrics.get('high_confidence_messages', 0):,}")
        print(f"Medium Confidence (50-79): {quality_metrics.get('medium_confidence_messages', 0):,}")
        print(f"Low Confidence (<50): {quality_metrics.get('low_confidence_messages', 0):,}")

    def test_enhanced_parser(self):
        """Test the enhanced parser with sample messages"""
        
        # Test messages that should be parsed as OTP
        otp_test_messages = [
            {
                'message': "<#> Your One-Time Password(OTP) for UTS Mobile Ticket is 3614 CRIS/UTS vDCETbbqddr",
                'sender': "UTS",
                'expected': 'parsed'
            },
            {
                'message': "676653 is the OTP for your Dream11 account. Do not share this with anyone. Dream11 will never call or message asking for OTP.",
                'sender': "DM-DREAM11",
                'expected': 'parsed'
            },
            {
                'message': "362835 is your OTP to login/register to your ZUPEE account. Do not share this with anyone. We will never call you asking for OTP. T&C apply Ref Id - iIiFwK30BUR",
                'sender': "DM-ZUPEE",
                'expected': 'parsed'
            },
            {
                'message': "Paytm never calls you asking for OTP. Sharing it with anyone gives them full access to your Paytm Account. Your OTP is 955980 ID: asasK/GTt2i",
                'sender': "VM-PAYTM",
                'expected': 'parsed'
            },
            {
                'message': "805732 is the One Time Password (OTP) to convert connection type of your Jio Number 9399843517 from Prepaid to Postpaid. Order Number: NO0000VVGU46. This OTP is valid for 10 mins only.",
                'sender': "JIO",
                'expected': 'parsed'
            }
        ]
        
        # Test messages that should be rejected
        rejection_test_messages = [
            {
                'message': "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517 For tips on how to manage data quota effectively, click https://youtu.be/ZFUDydctV78",
                'sender': "JIO",
                'expected': 'rejected'
            },
            {
                'message': "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR Clr Bal: Rs. 47,695.00 CR. Never share OTP/Password for EMI postponement or any reason.-CBoI",
                'sender': "CBoI",
                'expected': 'rejected'
            },
            {
                'message': "Webinar: Exploring the field of Psychology with an Honours degree On 2nd July, 5 PM. Regards, MIT-WPU. Register now: https://npfs.in/y0efch6KY",
                'sender': "MIT-WPU",
                'expected': 'rejected'
            },
            {
                'message': "Tap to reset your Instagram password: https://ig.me/1Ilu0lRRUpNTXOl",
                'sender': "Instagram",
                'expected': 'rejected'
            }
        ]
        
        print("\nTesting Enhanced OTP Parser:")
        print("=" * 80)
        
        print("\nTesting OTP Messages (should be PARSED):")
        print("-" * 50)
        
        otp_correct = 0
        for i, test_case in enumerate(otp_test_messages, 1):
            result = self.parse_single_message(test_case['message'], test_case['sender'])
            is_correct = result['status'] == test_case['expected']
            status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
            if is_correct:
                otp_correct += 1
            
            print(f"Test {i}: {status}")
            print(f"Message: {test_case['message'][:80]}...")
            print(f"Status: {result['status']}")
            print(f"Confidence: {result.get('confidence_score', 'N/A')}")
            
            if result['status'] == 'parsed':
                print(f"OTP Code: {result.get('otp_code')}")
                print(f"Company: {result.get('company_name')}")
                print(f"Purpose: {result.get('purpose')}")
            
            print("-" * 50)
        
        print("\nTesting Non-OTP Messages (should be REJECTED):")
        print("-" * 50)
        
        rejection_correct = 0
        for i, test_case in enumerate(rejection_test_messages, 1):
            result = self.parse_single_message(test_case['message'], test_case['sender'])
            is_correct = result['status'] == test_case['expected']
            status = "✓ CORRECT" if is_correct else "✗ INCORRECT"
            
            if is_correct:
                rejection_correct += 1
            
            print(f"Test {i}: {status}")
            print(f"Message: {test_case['message'][:80]}...")
            print(f"Status: {result['status']}")
            print(f"Confidence: {result.get('confidence_score', 'N/A')}")
            print(f"Reason: {result.get('reason', 'N/A')}")
            print("-" * 50)
        
        total_correct = otp_correct + rejection_correct
        total_tests = len(otp_test_messages) + len(rejection_test_messages)
        
        print(f"\nTest Results Summary:")
        print(f"OTP Detection Accuracy: {otp_correct}/{len(otp_test_messages)} ({(otp_correct/len(otp_test_messages)*100):.1f}%)")
        print(f"Rejection Accuracy: {rejection_correct}/{len(rejection_test_messages)} ({(rejection_correct/len(rejection_test_messages)*100):.1f}%)")
        print(f"Overall Accuracy: {total_correct}/{total_tests} ({((total_correct/total_tests)*100):.1f}%)")

    def analyze_single_message(self, message: str, sender_name: str = "") -> Dict:
        """Analyze a single message and return detailed breakdown"""
        
        clean_message = self.clean_text(message)
        clean_sender = self.clean_text(sender_name)
        combined_text = f"{clean_message} {clean_sender}"
        
        analysis = {
            'message': clean_message,
            'sender_name': clean_sender,
            'analysis_steps': {
                'has_otp_number': self.has_actual_otp_number(combined_text),
                'strong_otp_indicators': self.has_strong_otp_indicators(combined_text),
                'security_context': self.has_security_context(combined_text),
                'validity_context': self.has_validity_context(combined_text),
                'banking_context': self.is_strong_banking_context(combined_text),
                'promotional_context': self.is_promotional_message(combined_text),
                'is_true_otp': self.is_true_otp_message(combined_text),
            },
            'confidence_score': self.calculate_otp_confidence_score(clean_message, clean_sender),
        }
        
        # Get final parsing result
        parsing_result = self.parse_single_message(clean_message, clean_sender)
        analysis['final_result'] = parsing_result
        
        return analysis

    def export_detailed_report(self, results: Dict, output_prefix: str):
        """Export detailed analysis reports"""
        
        # Create summary report
        summary_file = f"{output_prefix}_summary_report.json"
        
        summary_report = {
            'metadata': results['metadata'],
            'summary_statistics': results['summary_statistics'],
            'key_insights': {
                'most_common_companies': list(results['summary_statistics']['distributions']['top_companies'].items())[:5],
                'most_common_purposes': list(results['summary_statistics']['distributions']['purposes'].items()),
                'most_common_expiry_times': list(results['summary_statistics']['distributions']['expiry_durations'].items())[:3],
            }
        }
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            print(f"Summary report saved: {summary_file}")
        except Exception as e:
            print(f"Error saving summary report: {e}")

    def interactive_message_analyzer(self):
        """Interactive tool to analyze individual messages"""
        
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
            
            analysis = self.analyze_single_message(message, sender)
            
            print(f"Confidence Score: {analysis['confidence_score']}")
            print(f"Final Status: {analysis['final_result']['status']}")
            
            if analysis['final_result']['status'] == 'parsed':
                result = analysis['final_result']
                print(f"OTP Code: {result.get('otp_code')}")
                print(f"Company: {result.get('company_name')}")
                print(f"Purpose: {result.get('purpose')}")
                print(f"Expiry: {result.get('expiry_duration')}")
                print(f"Security Warnings: {len(result.get('security_warnings', []))}")
                print(f"Reference ID: {result.get('reference_id')}")
                print(f"Phone Number: {result.get('phone_number')}")
            else:
                print(f"Rejection Reason: {analysis['final_result'].get('reason')}")
            
            print(f"\nDetailed Checks:")
            for check, value in analysis['analysis_steps'].items():
                print(f"  {check.replace('_', ' ').title()}: {value}")

def main():
    # Initialize enhanced parser
    parser = EnhancedOTPMessageParser()
    
    print("Enhanced OTP Message Parser with Smart Classification")
    print("=" * 80)
    print("This parser analyzes messages to identify OTP content using:")
    print("- Regex pattern matching")
    print("- Keyword analysis")
    print("- Fuzzy matching")
    print("- Context-aware classification")
    print("- Confidence scoring")
    
    # Test parser first
    test_parser = input("\nWould you like to test the parser with sample messages? (y/n): ").lower().strip()
    
    if test_parser == 'y':
        parser.test_enhanced_parser()
    
    # Interactive analyzer
    interactive_test = input("\nWould you like to test individual messages interactively? (y/n): ").lower().strip()
    
    if interactive_test == 'y':
        parser.interactive_message_analyzer()
    
    # Process CSV file
    process_csv = input(f"\nWould you like to process a CSV file? (y/n): ").lower().strip()
    
    if process_csv == 'y':
        # Get input file path
        input_file = input("Enter the path to your CSV file: ").strip().strip('"')
        
        if not input_file:
            print("No file path provided. Exiting.")
            return
        
        # Ask for output file path
        output_file = input("Enter output JSON file path (or press Enter for auto-naming): ").strip().strip('"')
        if not output_file:
            output_file = None
        
        print(f"\nProcessing file: {input_file}")
        print("Analyzing messages for OTP content...")
        print("Only messages identified as OTP will be parsed and included in output.")
        
        # Process the file
        results = parser.process_csv_file(input_file, output_file)
        
        if results:
            print(f"\nProcessing completed successfully!")
            
            # Ask for detailed report
            detailed_report = input("\nWould you like to generate a detailed analysis report? (y/n): ").lower().strip()
            if detailed_report == 'y':
                output_prefix = input_file.replace('.csv', '')
                parser.export_detailed_report(results, output_prefix)
            
            # Show sample results
            if results['metadata']['otp_messages_found'] > 0:
                show_samples = input("\nWould you like to see sample parsed OTP messages? (y/n): ").lower().strip()
                if show_samples == 'y':
                    n_samples = min(5, len(results['otp_messages']))
                    
                    print(f"\nSample Parsed OTP Messages ({n_samples} examples):")
                    print("=" * 80)
                    
                    for i, msg in enumerate(results['otp_messages'][:n_samples], 1):
                        print(f"\nExample {i}:")
                        print("-" * 40)
                        print(f"OTP Code: {msg.get('otp_code')}")
                        print(f"Company: {msg.get('company_name')}")
                        print(f"Purpose: {msg.get('purpose')}")
                        print(f"Validity: {msg.get('expiry_duration')}")
                        print(f"Security Warnings: {msg.get('security_warnings_text')}")
                        print(f"Reference ID: {msg.get('reference_id')}")
                        print(f"Phone Number: {msg.get('phone_number')}")
                        print(f"Sender: {msg.get('sender_name')}")
                        print(f"Confidence: {msg.get('confidence_score')}")
                        
                        message_preview = msg.get('raw_message', '')[:150]
                        print(f"Message: {message_preview}{'...' if len(msg.get('raw_message', '')) > 150 else ''}")
            else:
                print("\nNo OTP messages found in the dataset.")
                print("All messages were rejected as not related to OTP verification.")
            
            print(f"\nFinal Summary:")
            print(f"Input Messages: {results['metadata']['total_input_messages']:,}")
            print(f"OTP Messages Found: {results['metadata']['otp_messages_found']:,}")
            print(f"Detection Rate: {results['metadata']['otp_detection_rate']}%")
            
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
#             r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
#             r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
#             r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*(?:the\s*)?(?:otp|one\s*time\s*password)\s*for\s*your\s*\w+\s*account\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
#             r'\b(\d{4,8})\s*is\s*your\s*one\s*time\s*password\s*to\s*proceed\s*on\s*\w+',
#             r'\byour\s*otp\s*is\s*(\d{4,8})\s*id\s*:\s*\w+',  # Paytm style
#             r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\b',
#             r'\bto\s*(?:proceed|login|register|verify)\s*.*one\s*time\s*password\s*(\d{4,8})\b',
#             r'\bto\s*(?:register|login)\s*on\s*\w+\s*use\s*one\s*time\s*password\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\s*to\s*convert\s*connection\s*type\b',
#         ]
        
#         # Enhanced OTP classification patterns from classifier
#         self.true_otp_patterns = [
#             r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
#             r'\b(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*(\d{4,8})\b',
#             r'\buse\s*(?:otp|one\s*time\s*password)\s*(\d{4,8})\b',
#             r'\benter\s*(?:otp|code)\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*(?:the\s*)?(?:otp|one\s*time\s*password)\s*for\s*your\s*\w+\s*account\b',
#             r'\byour\s*(?:otp|one\s*time\s*password)\s*for\s*\w+\s*(?:login|account|registration)\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
#             r'\byour\s*otp\s*is\s*(\d{4,8})\s*id\s*:\s*\w+',
#             r'\b(\d{4,8})\s*is\s*the\s*one\s*time\s*password\s*\(otp\)\b',
#             r'\bto\s*(?:proceed|login|register|verify)\s*.*one\s*time\s*password\s*(\d{4,8})\b',
#             r'\bsharing\s*(?:it|otp)\s*with\s*anyone\s*gives\s*them\s*full\s*access.*your\s*otp\s*is\s*(\d{4,8})\b',
#             r'\b(\d{4,8}).*(?:valid\s*for|expires?\s*in)\s*\d+\s*(?:minutes?|mins?)\b',
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
#             r'\b\d{4,8}\b.*\b(?:otp|one\s*time\s*password)\b',
#             r'\b(?:otp|one\s*time\s*password)\b.*\b\d{4,8}\b',
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
#             'otp to register', 'use one time password', 'your one time password'
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
#             if pattern.search(text):
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
#         platforms = ['dream11', 'zupee', 'paytm', 'meesho', 'phonepe', 'ajio', 'jio']
        
#         for platform in platforms:
#             if platform in text_lower:
#                 if any(word in text_lower for word in ['account', 'login', 'register', 'proceed']):
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
#             r'\b(\d{4,8})\b.*(?:otp|one\s*time\s*password)',
#             r'(?:otp|one\s*time\s*password).*\b(\d{4,8})\b',
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
#         score += min(pattern_matches * 5, 20)  # Max 20 bonus points
        
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
        
#         # Determine if this is an OTP message (threshold: 60)
#         is_otp_message = confidence_score >= 60 and self.is_true_otp_message(combined_text)
        
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
#                 'parser_version': '2.0_enhanced'
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
#                 'medium_confidence_messages': sum(1 for score in confidence_scores if 60 <= score < 80),
#                 'low_confidence_messages': sum(1 for score in confidence_scores if score < 60),
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
#         print(f"Medium Confidence (60-79): {quality_metrics.get('medium_confidence_messages', 0):,}")
#         print(f"Low Confidence (<60): {quality_metrics.get('low_confidence_messages', 0):,}")

#     def test_enhanced_parser(self):
#         """Test the enhanced parser with sample messages"""
        
#         # Test messages that should be parsed as OTP
#         otp_test_messages = [
#             {
#                 'message': "676653 is the OTP for your Dream11 account. Do not share this with anyone. Dream11 will never call or message asking for OTP.",
#                 'sender': "DM-DREAM11",
#                 'expected': 'parsed'
#             },
#             {
#                 'message': "362835 is your OTP to login/register to your ZUPEE account. Do not share this with anyone. We will never call you asking for OTP. T&C apply Ref Id - iIiFwK30BUR",
#                 'sender': "DM-ZUPEE",
#                 'expected': 'parsed'
#             },
#             {
#                 'message': "Paytm never calls you asking for OTP. Sharing it with anyone gives them full access to your Paytm Account. Your OTP is 955980 ID: asasK/GTt2i",
#                 'sender': "VM-PAYTM",
#                 'expected': 'parsed'
#             },
#             {
#                 'message': "805732 is the One Time Password (OTP) to convert connection type of your Jio Number 9399843517 from Prepaid to Postpaid. Order Number: NO0000VVGU46. This OTP is valid for 10 mins only.",
#                 'sender': "JIO",
#                 'expected': 'parsed'
#             }
#         ]
        
#         # Test messages that should be rejected
#         rejection_test_messages = [
#             {
#                 'message': "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517 For tips on how to manage data quota effectively, click https://youtu.be/ZFUDydctV78",
#                 'sender': "JIO",
#                 'expected': 'rejected'
#             },
#             {
#                 'message': "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR Clr Bal: Rs. 47,695.00 CR. Never share OTP/Password for EMI postponement or any reason.-CBoI",
#                 'sender': "CBoI",
#                 'expected': 'rejected'
#             },
#             {
#                 'message': "Webinar: Exploring the field of Psychology with an Honours degree On 2nd July, 5 PM. Regards, MIT-WPU. Register now: https://npfs.in/y0efch6KY",
#                 'sender': "MIT-WPU",
#                 'expected': 'rejected'
#             },
#             {
#                 'message': "Tap to reset your Instagram password: https://ig.me/1Ilu0lRRUpNTXOl",
#                 'sender': "Instagram",
#                 'expected': 'rejected'
#             }
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