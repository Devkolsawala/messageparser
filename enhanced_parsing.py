import pandas as pd
import re
import json
from typing import Dict, List, Optional, Tuple
import time
from difflib import SequenceMatcher
from datetime import datetime

class EnhancedMessageParser:
    def __init__(self):
        # --- FIXED OTP Extraction Patterns ---
        self.otp_patterns = [
            # PRIORITY: Simple direct patterns first
            r'\b(\d{4,8})\s*is\s*your\s*(?:otp|one\s*time\s*password|verification\s*code|code)\b',
            r'(?:otp|code|password)\s*is\s*[:\s]*(\d{3}[- ]?\d{3})\b',
            r'\b(\d{3}[- ]?\d{3})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code)',
            r'enter\s*(\d{4,8})\s*to',
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code)',
            r'g-(\d{6})\b',
            r'otp[:\s]*(\d{4,8})\b',
            r'(\d{4,8})\s*from\s+\w+',
            r'verification\s*code[:\s]*(\d{4,8})',
            # FIXED: Added more direct patterns
            r'\b(\d{4,8})\s*is\s*your\s*otp\s*from\b',
            r'your\s*otp\s*is\s*(\d{4,8})\b',
            # ADDED: New flexible pattern for formats like "OTP to login... is 123456"
            r'\botp\b.*?is\s*(\d{4,8})\b',
        ]
        
        # --- FIXED EMI Amount Extraction Patterns ---
        self.emi_amount_patterns = [
            # PRIORITY: Fixed Rs. patterns with proper grouping
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*due',
            r'pay\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'emi\s*(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'emi\s*(?:amount\s*)?(?:is\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:loan\s*)?emi\s*(?:amount\s*)?(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)[/-]*\s*(?:for|is)\s*(?:your\s*)?(?:loan\s*)?emi',
            r'emi\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)[,\s]*(?:emi|loan)',
            r'dmi\s*(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:overdue|due)\s*(?:amount\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'pay\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:emi|dmi|loan)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*is\s*due',
            r'(?:installment|instalment)\s*(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*due\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'outstanding\s*(?:amount\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            # FIXED: New patterns for "to pay Rs.2150" format
            r'to\s*pay\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'click.*to\s*pay\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ]
        
        # --- EMI Due Date Patterns ---
        # --- ENHANCED: EMI Due Date Patterns ---
        self.emi_due_date_patterns = [
            # PRIORITY: High-precision patterns for common EMI message formats
            r'due\s*on\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'falls?\s*due\s*on\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'payable\s*on\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'due\s*date\s*(?:is\s*)?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            # Enhanced patterns for different date formats
            r'due\s*on\s*(\d{1,2}[-/][a-z]{3}[-/]\d{2,4})',  # due on 05-Jul-24
            r'falls?\s*due\s*on\s*(\d{1,2}[-/][a-z]{3}[-/]\d{2,4})',
            r'payable\s*on\s*(\d{1,2}[-/][a-z]{3}[-/]\d{2,4})',
            # Generic date patterns with context
            r'(?:pay\s*)?(?:by\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'for\s*([a-z]{3}\'?\d{4})',  # Jul'2024
            r'for\s*(?:the\s*month\s*of\s*)?([a-z]{3,9}\s*\d{4})',  # July 2024
            r'last\s*emi\s*payment.*?for[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'ending\s*on[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:overdue|outstanding)\s*since\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # Enhanced specific patterns
            r'emi.*?due.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'installment.*?due.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'payment.*?due.*?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        # --- ENHANCED: Traffic Challan Patterns ---
        self.challan_number_patterns = [
            r'challan\s*(?:bearing\s*)?(?:no\.?\s*)?([A-Z]{2}\d{17,20})',
            r'challan\s*(?:no\.?\s*)?([A-Z]{2}\d{17,20})',
            r'vide\s*challan\s*(?:no\.?\s*)?([A-Z]{2}\d{17,20})',
            r'challan\s*(?:number\s*)?([A-Z]{2}\d{14,20})',
            r'challan\s*(?:reference\s*)?(?:number\s*)?[:\s]*([A-Z0-9]{8,20})',
            r'(?:reference\s*)?(?:number\s*)?([A-Z0-9]{8,20})\s*for\s*payment',
            r'challan\s*(?:number\s*)?[:\s]*([A-Z]{2}\d{15,20})',
            r'(?:for\s*)?([A-Z]{2}[A-Z0-9]{10,20})\s*has\s*been\s*received',
            r'payment.*?for\s*([A-Z]{2}[A-Z0-9]{10,20})',
            r'challan\s*(?:no\.?\s*|number\s*)?[:\s]*([A-Z0-9]{10,25})',
            r'vide\s*challan\s*(?:no\.?\s*)?(\d{8,12})',
            r'challan\s*(?:no\.?\s*)?(\d{8,12})\b',
            r'challan\s*([A-Z]{2}\d{10,20})\s*issued',
            r'challan\s*bearing\s*no\.?\s*([A-Z0-9]{8,25})\s*.*?(?:court|disposal)',
            r'bearing\s*no\.?\s*([A-Z0-9]{8,25})\s*.*?sent\s*to\s*court'
        ]
        
        self.vehicle_number_patterns = [
            r'vehicle\s*no\.?\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'vehicle\s*(?:number\s*)?[:\s]*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'against\s*your\s*vehicle\s*(?:number\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'for\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'by\s*your\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'vehicle\s*(?:registration\s*)?(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'issued\s*against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'no\.?\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})\s*(?:dated|is|sent)',
            r'([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})\s*dated'
        ]
        
        self.challan_fine_patterns = [
            r'fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'pay\s*fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'penalty\s*(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[/-]*\s*fine',
            r'fine\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'payment\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'for\s*payment\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'total\s*(?:challan\s*)?amount[:\s]*rs?\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'total\s*(?:challan\s*)?amount[:\s]*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount[:\s]*(\d+(?:,\d{3})*(?:\.\d{1,2})?)(?:\s*rs?\.?)?(?:\s*[.-]|$)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*has\s*been\s*(?:initiated|received)',
            r'the\s*total\s*challan\s*amount\s*is\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'challan\s*amount\s*is\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'fine\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*DDCSMS'
        ]
        
        self.payment_link_patterns = [
            r'(https?://[^\s]+)',
            r'click\s*(https?://[^\s]+)',
            r'visit\s*(https?://[^\s]+)',
            r'logon\s*to\s*(https?://[^\s]+)',
            r'(https?://[a-zA-Z0-9.-]+[^\s]*)',
            r'(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)',
            r'click\s*here:\s*(https?://[^\s]+)',
            r'visit:\s*(https?://[^\s]+)'
        ]
        
        # --- FIXED: TRANSPORTATION MESSAGE PARSING PATTERNS ---
        # PNR Patterns for different transportation modes
        self.pnr_patterns = [
            r'pnr\s*[:\-]?\s*(\d{10})\b',
            r'pnr\s*(?:number|no)?\s*[:\-]?\s*(\d{10})\b',
            r'pnr\s*(?:is\s*)?([A-Z0-9]{6})\s*[-\s]',
            r'(?:your\s*)?(?:indigo\s*)?pnr\s*(?:is\s*)?([A-Z0-9]{6})\b',
            r'bus\s*pnr\s*[:\-]?\s*([A-Z0-9]{8,12})\b',
            r'pnr\s*[:\-]?\s*([A-Z]\d{9})\b',
            r'booking\s*(?:reference|ref)\s*[:\-]?\s*([A-Z0-9]{6,12})\b',
            r'confirmation\s*(?:number|no)\s*[:\-]?\s*([A-Z0-9]{6,12})\b',
        ]
        
        # Date of Journey Patterns
        self.doj_patterns = [
            r'doj\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'dt\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'date\s*of\s*journey\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'travel\s*date\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'journey\s*date\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[a-z]{3})\b',
            r'(\d{1,2}\s*[a-z]{3,9}\s*\d{2,4})',
            r'doj:\s*(\d{1,2}[-/][a-z]{3}[-/]\d{4}\s*\d{2}:\d{2})',
            r'(?:\bdoj|boardingdate)\s*[:\-]?\s*(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b',
        ]
        
        # FIXED: Enhanced route patterns with better specificity
        self.route_patterns = [
            # PRIORITY: High-specificity patterns first
            r'(?:frm|from)\s+([A-Z]{2,5})\s+to\s+([A-Z]{2,5})\b',
            r'\b([A-Z]{3})\(T\d?\)[-\s]*([A-Z]{3})',  # Flight routes with terminals
            r'([A-Z]{3})[-\s]([A-Z]{3})\s*\d{4}[-\s]\d{4}',  # Flight with times
            # Route patterns with proper city name extraction
            r'route\s*[:\-]?\s*([A-Z][a-zA-Z\s]{3,25})\s*[-to]\s*([A-Z][a-zA-Z\s]{3,25})',
            r'from\s+([A-Z][a-zA-Z\s]{3,25})\s+to\s+([A-Z][a-zA-Z\s]{3,25})',
            r'dep[:\s]+([A-Z][a-zA-Z\s]{3,25})\s+arr[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            # FIXED: Be more careful with generic patterns - avoid single words
            r'\b([A-Z]{3,5})[-\s]([A-Z]{3,5})\b(?!\s*(?:shall|from|to|gate|boarding))',
        ]
        
        # FIXED: Enhanced boarding place patterns - avoid single words
        self.boarding_place_patterns = [
            # High priority: specific patterns with context
            r'boarding\s*(?:station|point)?\s*(?:is|:)?\s*([a-zA-Z\s\d]{4,30}?)\s*-\s*([A-Z]{3,5})',
            r'boarding\s*(?:at|from|:)\s*([a-zA-Z\s,]{4,30}?)(?:\s*at\s*\d{2}:\d{2})',
            r'dep[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'departure[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'pickup[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'boarding\s*point[:\s]*([A-Z][a-zA-Z\s,]{4,30})',
            # FIXED: Airport code extraction with proper context
            r'flight\s*\d+\s*from\s*([A-Z]{3})\b',
        ]
        
        self.drop_place_patterns = [
            r'destination\s*(?:station|point)?\s*(?:is|:)?\s*([a-zA-Z\s\d]{4,30}?)\s*-\s*([A-Z]{3,5})',
            r'arrival\s*at\s*([a-zA-Z\s,]{4,30})',
            r'arr[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'arrival[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'drop[:\s]+([A-Z][a-zA-Z\s]{3,25})',
            r'dropping\s*point[:\s]*([A-Z][a-zA-Z\s,]{4,30})',
        ]
        
        # FIXED: Enhanced seat information patterns
        # ENHANCED: Enhanced seat information patterns with better specificity
        self.seat_patterns = [
            # Flight seat patterns - more specific with better context filtering
            r'seat\s*(?:no\.?|nos\.?)?[:\s]*([A-Z]?\d{1,3}[A-Z]?)(?:\s*,\s*([A-Z]?\d{1,3}[A-Z]?))*\b(?!\s*(?:from|shall|gate|closes|mins|prior))',
            r'seats?\s*([A-Z]?\d{1,3}[A-Z]?(?:[,\s]+[A-Z]?\d{1,3}[A-Z]?)*)\b(?!\s*(?:from|shall|gate|closes|mins|prior))',
            # Train seat patterns with enhanced specificity
            r'\b(?:CNF|WL|RAC)/([A-Z0-9]+)/([\d,\s&]+)\b',
            r'P\d[-]([A-Z0-9]+)[,]([\d,\s&]+)\b',
            r',\s*([A-Z0-9]{1,4})\s+([\d,\s&]+)\b',
            r'\b([A-Z0-9]{1,4})[,]\s*([\d]+)\b',
            r'(?:coach|trn)\s*[:\-]?\s*([A-Z0-9]+)\s*[,]\s*(?:berth|seat)\s*[:\-]?\s*([\d,\s&]+)\b',
            r'\b([A-Z]+\d+)\s*[,]\s*([\d,\s]+)[,]\s*(?:SL|3A|2A|1A|CC|2S)\b',
            r'berth\s*[:\-]?\s*([A-Z0-9,\s]+)\b',
            # Bus seat patterns
            r'bus.*?seat\s*(?:no\.?)?[:\s]*([A-Z0-9,\s-]+)',
            r'(?:allocated\s*)?seats?\s*([A-Z]?\d{1,2}(?:[,\s]*[A-Z]?\d{0,2})*)',
            # Enhanced gate extraction to avoid confusion with seats
            r'gate\s*(\d+)(?:\s*(?:closes|boarding))',  # Only gate with context
        ]
        
        # FIXED: Enhanced class patterns
        self.class_patterns = [
            r'\b(2S)\b',
            r'\b(SL|3A|2A|1A|CC)\b',
            r'(?:class|cl|cls)\s*[:\-]?\s*([A-Z\s/]+)\b',
            r'\b(Sleeper|AC\s*3\s*Tier|AC\s*2\s*Tier|AC\s*First\s*Class|AC\s*Chair\s*Car)\b',
            r'\b(Economy|Business|First\s*Class)\b',
            r'\b(A/C\s*Sleeper|Non\s*A/C\s*Seater)\b',
            r'\b(AC|Non-AC|Sleeper|Semi-Sleeper|Seater)\b'
        ]
        
        # Enhanced Platform and Gate patterns
        self.platform_patterns = [
            r'\b(?:platform|plat|pf)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z]?\d{1,2})\b'
        ]
        
        # Enhanced Gate patterns with better context specificity
        self.gate_patterns = [
            # ENHANCED: More specific gate patterns with better context
            r'\bgate\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9]+)(?:\s*(?:closes|boarding|departure))?',
            r'boarding\s*(?:from\s*)?gate\s*(?:no\.?)?\s*([A-Z0-9]+)\b',
            r'gate\s*([A-Z0-9]+)(?:\.\s*boarding|\s*shall\s*be)',
            r'from\s*gate\s*([A-Z0-9]+)\b',
            # Enhanced to avoid confusion with other numbers
            r'(?:boarding\s*from\s*|from\s*)gate\s*(\d+)(?!\s*(?:minutes?|mins?|hours?|hrs?))',
        ]
        
        # Enhanced departure time patterns
        self.departure_time_patterns = [
            r'dp\s*[:\-]?\s*(\d{1,2}:\d{2})',
            r'departure\s*[:\-]?\s*(\d{1,2}:\d{2})',
            r'boarding\s*at\s*(\d{1,2}:\d{2})',
            r'(\d{2}:\d{2})[-\s](?:\d{2}:\d{2})\s*hrs?',
            r'dep\s*[:\-]?\s*(\d{1,2}:\d{2})',
        ]
        
        # Enhanced bus number patterns
        self.bus_number_patterns = [
            r'bus\s*no\.?\s*[:\-]?\s*([A-Z0-9-]+)',
            r'vehicle\s*no\.?\s*[:\-]?\s*([A-Z0-9-]+)',
            r'bus\s*number\s*[:\-]?\s*([A-Z0-9-]+)',
            r'service\s*no\.?\s*[:\-]?\s*([A-Z0-9-]+)',
        ]
        
        # Enhanced flight number patterns with better specificity
        self.flight_number_patterns = [
            # ENHANCED: More precise flight number patterns
            r'flight\s*(?:no\.?\s*)?(\d+[A-Z]?)\b',  # flight 762, flight no 123A
            r'flight\s*([A-Z]{2}\s*\d+)\b',  # flight AI 123
            r'(\d+[A-Z]?)\s*from\s*[A-Z]{3}',  # 762 from BHO
            r'([A-Z]{2}\s*\d+[A-Z]?)\s*from',  # AI 762A from
            r'flight\s*number\s*[:\-]?\s*([A-Z0-9]+)',
            r'([A-Z]{2}-?\d+[A-Z]?)\b(?!\s*(?:gate|mins|hours?))',  # AI-762, 6E123 (excluding gate numbers)
            # IndiGo and other airline specific patterns
            r'indigo.*?flight\s*(\d+[A-Z]?)',
            r'(?:indigo|spicejet|air\s*india|vistara).*?(\d+[A-Z]?)\s*from',
        ]
        
        # Mapping for train class abbreviations
        self.train_class_map = {
            'SL': 'Sleeper', '3A': 'AC 3 Tier', 'B': 'AC 3 Tier',
            '2A': 'AC 2 Tier', 'A': 'AC 2 Tier', '1A': 'AC First Class', 'H': 'AC First Class',
            'CC': 'AC Chair Car', 'C': 'AC Chair Car', 'S': 'Sleeper', '2S': 'Second Seating',
            'SLEEPER CLASS': 'Sleeper', 'THIRD AC': 'AC 3 Tier'
        }
        
        # Transportation Service Providers
        self.transport_providers = {
            'Train': [
                r'\birctc\b', r'\bindian\s*railway?\b', r'\brailway\b',
                r'train\s*no\s*[:\-]?\s*\d+', r'trn\s*[:\-]?\s*\d+',
                r'chart\s*prepared', r'pnr\s*[:\-]?\s*\d{10}',
                r'qr\s*code.*indianrail'
            ],
            'Flight': [
                r'\bindigo\b', r'\bspicejet\b', r'\bair\s*india\b', r'\bvistara\b',
                r'\bgoair\b', r'\bakasa\s*air\b', r'\bjet\s*airways\b',
                r'flight\s*\d+[A-Z]?', r'\d+[A-Z]?\s*from', r'web\s*check[-\s]in',
                r'terminal\s*[T]?\d', r'departure.*arrival', r'boarding',
                r'gate\s*\d+', r'boarding\s*gate'
            ],
            'Bus': [
                r'\bksrtc\b', r'\bmsrtc\b', r'\btsrtc\b', r'\bapsrtc\b',
                r'\brstc\b', r'\bupsrtc\b', r'\bmksrtc\b',
                r'bus\s*no\s*[:\-]?\s*[A-Z0-9]+', r'crew\s*mobile',
                r'happy\s*journey', r'bus\s*pnr',
                r'\bambay\b', r'\bmb\s*travels\b', r'\bmadhav\b', r'\bsanjeev\b', r'\bshree\b'
            ]
        }
        
        # Time patterns for transportation (generic)
        self.time_patterns = [
            r'(\d{2}:\d{2})[-\s](\d{2}:\d{2})\s*hrs?',
            r'(\d{1,2}:\d{2})',
        ]
        
        # Transportation specific indicators
        self.transportation_indicators = [
            r'\bpnr\b', r'\bdoj\b', r'\btrn\b', r'\bdt\b',
            r'\bflight\b', r'\btrain\b', r'\bbus\b',
            r'\bjourney\b', r'\bboarding\b', r'\bdeparture\b',
            r'\barrival\b', r'\btravel\b', r'\broute\b',
            r'\bconfirm\b', r'\bbooking\b', r'\bticket\b',
            r'\bfare\b', r'\bseat\b', r'\bberth\b',
            r'\bterminal\b', r'\bplatform\b', r'\bgate\b', r'\bcoach\b'
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
            r'\bonline\s*lok\s*adalat\b',
            r'\bsama\.live\b',
            r'\btraffic\s*violations\b',
            r'\bfound\s*actionable\b',
            r'\bissued\s*against\b',
            r'\bnotice\s*branch\b',
            r'\bddcsms\b',
            r'\bcourt\s*for\s*disposal\b',
            r'\bsent\s*to\s*court\b',
            r'\bdisposal\s*as\s*per\s*law\b',
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
            ],
            'court_disposal': [
                r'sent\s*to\s*court\s*for\s*disposal',
                r'court\s*for\s*disposal',
                r'disposal\s*as\s*per\s*law',
                r'sent\s*to\s*virtual\s*court',
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
            'Sama Platform': [r'sama\.live', r'sama\s*platform'],
            'Online Lok Adalat': [r'online\s*lok\s*adalat'],
        }
        
        # --- FIXED: Bank/Lender Name Patterns ---
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
            'TVS Credit': [r'tvs\s*credit'],
            'Mash Technologies': [r'mash\s*technologies', r'theemiclub'],
            'Fusion Microfinance': [r'fusion\s*microfinance'],
            'Buddy Loan': [r'buddy\s*loan'],  # FIXED: Added Buddy Loan
        }
        
        # --- FIXED: Account Number Patterns ---
        self.account_number_patterns = [
            # PRIORITY: More specific patterns first
            r'a[/c]*\s*#\s*(\d{6,20})',  # A/C #3089560105
            r'for\s*a[/c]*\s*#?\s*([A-Z0-9]{6,20})',  # for A/C #3089560105
            r'loan\s*a[/c]*[:\s]*(\d{6,20})',
            r'loan\s*a[/c]*[:\s]*([A-Z0-9]{6,20})',
            r'account\s*(?:number|no)[:\s]*(\d{6,20})',
            r'account\s*(?:number|no)[:\s]*([A-Z0-9]{6,20})',
            r'loan\s*account[:\s]*(\d{6,20})',
            r'loan\s*account[:\s]*([A-Z0-9]{6,20})',
            r'a[/c]*[:\s]*(\d{6,20})(?:\D|$)',
            r'a[/c]*[:\s]*([A-Z0-9]{6,20})(?:\D|$)',
            r'account[:\s]*(\d{6,20})(?:\D|$)',
            r'account[:\s]*([A-Z0-9]{6,20})(?:\D|$)',
            # For masked account numbers like Ac XX9122
            r'ac\s*([xX\d]+)\b',
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
            r'\brepayment\b',
            r'\bdmi\b',
            r'\btheemiclub\b',
            r'\bmash\s*technologies\b',
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
        
        # --- NEW: EPF Contribution Patterns ---
        self.epf_indicators = [
            r'\bepf\b', r'\bepfo\b', r'\buan\b', r'provident\s*fund', r'accumulations'
        ]
        self.uan_patterns = [
            r'uan\s*(?:no\.?|number)?\s*[:\-]?\s*(\b10\d{10}\b)',
            r'against\s*uan\s*(\b10\d{10}\b)',
        ]
        self.epf_amount_patterns = [
            r'contribution\s*of\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*credited.*epf',
            r'credited\s*\(trf\)\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ]
        self.available_balance_patterns = [
            r'avl\s*bal\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)'
        ]

        # --- General Keywords & Patterns for Confidence Scoring ---
        self.true_otp_patterns = [
            r'\b(otp|one[- ]?time[- ]?password|verification code|login code|registration code)\b',
            r'\b(enter\s*[\d-]+)\b',
            r'(\d{4,8})\s*is\s*your',
            r'(\d{4,8})\s*from\s+\w+',
            # FIXED: Added more direct patterns for OTP detection
            r'\b(\d{4,8})\s*is\s*your\s*otp\s*from\b',
        ]
        
        # --- FIXED: Company & Service Keywords for OTP ---
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
            'Buddy Loan': [r'\bbuddy\s*loan\b'],  # FIXED: Added Buddy Loan
            'Mobipocket': [r'\bmobipocket\b'],
            'EPFO': [r'\bepfo\b'], # NEW: Added EPFO
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
        # Transportation pattern compilation
        self.compiled_pnr_patterns = [re.compile(p, re.IGNORECASE) for p in self.pnr_patterns]
        self.compiled_doj_patterns = [re.compile(p, re.IGNORECASE) for p in self.doj_patterns]
        self.compiled_route_patterns = [re.compile(p, re.IGNORECASE) for p in self.route_patterns]
        self.compiled_boarding_place_patterns = [re.compile(p, re.IGNORECASE) for p in self.boarding_place_patterns]
        self.compiled_drop_place_patterns = [re.compile(p, re.IGNORECASE) for p in self.drop_place_patterns]
        self.compiled_seat_patterns = [re.compile(p, re.IGNORECASE) for p in self.seat_patterns]
        self.compiled_class_patterns = [re.compile(p, re.IGNORECASE) for p in self.class_patterns]
        self.compiled_time_patterns = [re.compile(p, re.IGNORECASE) for p in self.time_patterns]
        self.compiled_transportation_indicators = [re.compile(p, re.IGNORECASE) for p in self.transportation_indicators]
        self.compiled_platform_patterns = [re.compile(p, re.IGNORECASE) for p in self.platform_patterns]
        self.compiled_gate_patterns = [re.compile(p, re.IGNORECASE) for p in self.gate_patterns]
        self.compiled_departure_time_patterns = [re.compile(p, re.IGNORECASE) for p in self.departure_time_patterns]
        self.compiled_bus_number_patterns = [re.compile(p, re.IGNORECASE) for p in self.bus_number_patterns]
        self.compiled_flight_number_patterns = [re.compile(p, re.IGNORECASE) for p in self.flight_number_patterns]
        # NEW: EPF pattern compilation
        self.compiled_epf_indicators = [re.compile(p, re.IGNORECASE) for p in self.epf_indicators]
        self.compiled_uan_patterns = [re.compile(p, re.IGNORECASE) for p in self.uan_patterns]
        self.compiled_epf_amount_patterns = [re.compile(p, re.IGNORECASE) for p in self.epf_amount_patterns]
        self.compiled_available_balance_patterns = [re.compile(p, re.IGNORECASE) for p in self.available_balance_patterns]

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
        # Transportation provider patterns
        self.compiled_transport_providers = {}
        for provider, patterns in self.transport_providers.items():
            self.compiled_transport_providers[provider] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def clean_text(self, text: str) -> str:
        """Clean the input text"""
        if pd.isna(text): return ""
        return str(text).strip()

    # --- TRANSPORTATION PARSING METHODS ---

    def extract_pnr_number(self, text: str) -> Optional[str]:
        """Extract PNR number from transportation messages"""
        text_upper = text.upper()
        for pattern in self.compiled_pnr_patterns:
            match = pattern.search(text_upper)
            if match:
                pnr = match.group(1)
                # Validate PNR format
                if self.is_valid_pnr(pnr):
                    return pnr
        return None

    def is_valid_pnr(self, pnr: str) -> bool:
        """Validate PNR format based on transportation type"""
        pnr = pnr.strip()
        # Train PNR: 10 digits
        if len(pnr) == 10 and pnr.isdigit():
            return True
        # Flight PNR: 6 alphanumeric characters
        if len(pnr) == 6 and re.match(r'^[A-Z0-9]+', pnr):
            return True
        # Bus PNR: Variable format (8-12 characters)
        if 8 <= len(pnr) <= 12 and re.match(r'^[A-Z0-9]+', pnr):
            return True
        return False

    def extract_date_of_journey(self, text: str) -> Optional[str]:
        """Extract date of journey from transportation messages"""
        for pattern in self.compiled_doj_patterns:
            match = pattern.search(text)
            if match:
                date_str = match.group(1)
                return self.normalize_transport_date(date_str)
        return None

    def normalize_transport_date(self, date_str: str) -> str:
        """Normalize various date formats to standard format"""
        date_str = date_str.strip().replace('|', '')
        # Handle DD-Mon-YYYY format e.g., 01-Jun-2024
        try:
            dt_obj = datetime.strptime(date_str, '%d-%b-%Y')
            return dt_obj.strftime('%d-%m-%Y')
        except ValueError:
            pass
        # Handle DD-Mon-YY format e.g., 04-Feb-24
        try:
            dt_obj = datetime.strptime(date_str, '%d-%b-%y')
            return dt_obj.strftime('%d-%m-%Y')
        except ValueError:
            pass
        # Handle formats like 14Nov
        if re.match(r'^\d{1,2}[a-z]{3}', date_str, re.IGNORECASE):
            return date_str
        # Handle DD-MM-YY or DD/MM/YY formats
        date_match = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', date_str)
        if date_match:
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = "20" + year
            return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
        # Handle date-time formats like 08-Jun-2024 18:15
        datetime_match = re.match(r'^(\d{1,2}[-/][a-z]{3}[-/]\d{4})\s*(\d{2}:\d{2})', date_str, re.IGNORECASE)
        if datetime_match:
            return datetime_match.group(0)
        return date_str

    # FIXED: Enhanced boarding place extraction with better validation
    def extract_boarding_place(self, text: str) -> Optional[str]:
        """FIXED: Enhanced boarding place extraction for all transport types"""
        # First, try flight-specific patterns for airport codes
        flight_from_match = re.search(r'flight\s*\d+\s*from\s*([A-Z]{3})\b', text, re.IGNORECASE)
        if flight_from_match:
            return flight_from_match.group(1)
        
        # Then, try high-precision route patterns for codes
        for pattern in self.compiled_route_patterns:
            match = pattern.search(text)
            if match and match.group(1) not in ['FROM', 'TO', 'GATE', 'SHALL']:  # FIXED: Exclude bad matches
                place = match.group(1).strip()
                if len(place) >= 3 and place not in ['from', 'shall', 'gate']:  # FIXED: Better validation
                    return place
        
        # Then, try patterns with keywords like "boarding", "departure", "pickup"
        for pattern in self.compiled_boarding_place_patterns:
            match = pattern.search(text)
            if match:
                place = match.group(1).strip()
                # FIXED: Clean and validate
                place = re.sub(r'^(dep|departure|boarding|pickup)[:\s]*', '', place, flags=re.IGNORECASE)
                place = re.sub(r'\s*-\s*[A-Z]{2,5}', '', place)  # Remove trailing codes
                if len(place) >= 3 and place.lower() not in ['from', 'shall', 'gate', 'to']:  # FIXED: Better exclusions
                    return place[:30].strip()
        return None

    # FIXED: Enhanced drop place extraction with better validation
    def extract_drop_place(self, text: str) -> Optional[str]:
        """FIXED: Enhanced drop place extraction for all transport types"""
        # First, try high-precision route patterns for codes
        for pattern in self.compiled_route_patterns:
            match = pattern.search(text)
            if match and match.lastindex >= 2:
                place = match.group(2).strip()
                if len(place) >= 3 and place.lower() not in ['from', 'shall', 'gate', 'to']:  # FIXED: Better validation
                    return place
        
        # Then, try patterns with keywords like "destination", "arrival", "drop"
        for pattern in self.compiled_drop_place_patterns:
            match = pattern.search(text)
            if match:
                place = match.group(1).strip()
                # Clean and return the best match
                place = re.sub(r'^(arr|arrival|destination|drop)[:\s]*', '', place, flags=re.IGNORECASE)
                place = re.sub(r'\s*-\s*[A-Z]{2,5}', '', place)  # Remove trailing codes
                if len(place) >= 3 and place.lower() not in ['from', 'shall', 'gate', 'to']:  # FIXED: Better exclusions
                    return place[:30].strip()
        return None

    def extract_transport_provider(self, text: str, sender_name: str = "") -> Optional[str]:
        """Extract transportation service provider from message"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        
        # Check for specific providers
        for provider_type, patterns in self.compiled_transport_providers.items():
            if any(p.search(combined_text) for p in patterns):
                # Try to get more specific provider name
                if provider_type == 'Train':
                    if 'irctc' in combined_text:
                        return 'IRCTC'
                    elif 'indian railway' in combined_text:
                        return 'Indian Railway'
                    else:
                        return 'Railway'
                elif provider_type == 'Flight':
                    # Extract specific airline
                    airlines = ['indigo', 'spicejet', 'air india', 'vistara', 'goair', 'akasa air']
                    for airline in airlines:
                        if airline in combined_text:
                            return airline.title()
                    return 'Airline'
                elif provider_type == 'Bus':
                    # Extract specific bus service
                    bus_services = ['ksrtc', 'msrtc', 'tsrtc', 'apsrtc', 'rsrtc', 'upsrtc', 'mksrtc']
                    for service in bus_services:
                        if service in combined_text:
                            return service.upper()
                    # Check for specific bus operators
                    bus_operators = {
                        'ambay': 'Ambay Travels', 'mb travels': 'M B Travels', 
                        'madhav': 'Madhav Travels', 'sanjeev': 'Sanjeev Travels', 
                        'shree': 'Shree Travels'
                    }
                    for operator, name in bus_operators.items():
                        if operator in combined_text:
                            return name
                    return 'Bus Service'
        return None

    # FIXED: Enhanced seat information extraction with better filtering
    def extract_seat_info(self, text: str) -> Optional[str]:
        """ENHANCED: Enhanced seat, coach, and berth information extraction with improved context filtering"""
        all_seats = []
        
        # Search for seat patterns across the entire text
        for pattern in self.compiled_seat_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract groups and clean them
                groups = [group.strip().rstrip('.,;') for group in match.groups() if group and group.strip()]
                # ENHANCED: Better filtering with context awareness
                for seat in groups:
                    # Skip if it's clearly not a seat (enhanced exclusions)
                    if seat.lower() in ['from', 'shall', 'gate', 'to', 'mins', 'prior', 'closes', 'boarding', 'departure', 'time', 'flight']:
                        continue
                    
                    # Skip if it's a time pattern (HH:MM format)
                    if re.match(r'^\d{1,2}:\d{2}', seat):
                        continue
                    
                    # Enhanced gate number detection - if "gate" appears nearby, it's likely a gate number, not a seat
                    match_start = match.start()
                    match_end = match.end()
                    context_before = text[max(0, match_start-20):match_start].lower()
                    context_after = text[match_end:match_end+20].lower()
                    
                    if ('gate' in context_before or 'gate' in context_after) and seat.isdigit() and len(seat) <= 2:
                        continue  # Skip gate numbers that are mistaken for seats
                    
                    # Enhanced validation for reasonable seat formats
                    if len(seat.strip()) > 0 and not seat.isspace():
                        # For flight seats, expect alphanumeric format (e.g., 12A, 15F) or pure numbers
                        if re.match(r'^[A-Z]?\d{1,3}[A-Z]?$', seat) or re.match(r'^[\d,\s&]+$', seat):
                            all_seats.append(seat)
                        # For train seats, allow complex formats
                        elif re.match(r'^[A-Z0-9,\s&]+$', seat) and len(seat) <= 20:
                            all_seats.append(seat)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_seats = []
        for seat in all_seats:
            if seat not in seen and len(seat.strip()) > 0:
                seen.add(seat)
                unique_seats.append(seat)
        
        # ENHANCED: Return combined seat info with better validation
        if unique_seats:
            # Additional filtering for obviously wrong entries
            filtered_seats = []
            for seat in unique_seats:
                # Skip if it contains common non-seat words
                if not any(word in seat.lower() for word in ['from', 'shall', 'gate', 'boarding', 'closes', 'mins', 'prior', 'departure', 'time']):
                    # Skip standalone numbers that are likely not seats in flight context
                    if seat.isdigit() and len(seat) <= 2 and 'flight' in text.lower():
                        # Check if this number appears with "gate" context
                        if f'gate {seat}' in text.lower() or f'gate{seat}' in text.lower():
                            continue
                    filtered_seats.append(seat)
            
            return ", ".join(filtered_seats) if filtered_seats else None
        return None

    def extract_class_info(self, text: str, transport_type: str) -> Optional[str]:
        """Enhanced travel class information extraction"""
        potential_matches = []
        for pattern in self.compiled_class_patterns:
            match = pattern.search(text)
            if match:
                class_candidate = match.group(1).upper().strip()
                # FIXED: Skip invalid class matches
                if class_candidate.lower() not in ['oses', 'from', 'shall', 'gate', 'mins']:
                    potential_matches.append(class_candidate)

        if not potential_matches:
             return None

        class_info = potential_matches[0]

        if transport_type == 'train':
            return self.train_class_map.get(class_info, class_info.title())
        elif transport_type == 'bus':
            # Enhanced bus class mapping
            bus_class_map = {
                'AC': 'AC', 'NON-AC': 'Non-AC', 'SLEEPER': 'Sleeper',
                'SEMI-SLEEPER': 'Semi-Sleeper', 'SEATER': 'Seater'
            }
            return bus_class_map.get(class_info, class_info.title())
        return class_info.title()

    def extract_platform_number(self, text: str) -> Optional[str]:
        """Extract platform number for train messages"""
        for pattern in self.compiled_platform_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip().upper()
        return None

    def extract_gate_number(self, text: str) -> Optional[str]:
        """ENHANCED: Enhanced gate number extraction for flight messages with better context awareness"""
        text_lower = text.lower()
        
        # Enhanced gate extraction with context validation
        for pattern in self.compiled_gate_patterns:
            match = pattern.search(text)
            if match:
                gate_num = match.group(1).strip().upper()
                
                # Enhanced validation: ensure it's actually a gate context
                match_start = match.start()
                match_end = match.end()
                context_before = text[max(0, match_start-30):match_start].lower()
                context_after = text[match_end:match_end+30].lower()
                
                # Strong gate indicators in context
                gate_indicators = ['boarding', 'departure', 'closes', 'flight', 'terminal']
                has_gate_context = any(indicator in context_before or indicator in context_after 
                                    for indicator in gate_indicators)
                
                # Validate gate number format (typically 1-3 characters)
                if len(gate_num) <= 3 and has_gate_context:
                    return gate_num
                elif 'gate' in text_lower and len(gate_num) <= 3:
                    # If "gate" is explicitly mentioned, it's likely a gate number
                    return gate_num
        
        return None

    def extract_departure_time(self, text: str) -> Optional[str]:
        """Enhanced departure time extraction"""
        for pattern in self.compiled_departure_time_patterns:
            match = pattern.search(text)
            if match:
                time_str = match.group(1).strip()
                # Basic validation: check if it looks like HH:MM
                if re.match(r'^\d{1,2}:\d{2}', time_str):
                    return time_str
        return None

    def extract_bus_number(self, text: str) -> Optional[str]:
        """Extract bus number from bus messages"""
        for pattern in self.compiled_bus_number_patterns:
            match = pattern.search(text)
            if match:
                bus_num = match.group(1).strip()
                # Basic validation
                if len(bus_num) >= 2 and any(c.isalnum() for c in bus_num):
                    return bus_num
        return None

    def extract_flight_number(self, text: str) -> Optional[str]:
        """Extract flight number from flight messages"""
        for pattern in self.compiled_flight_number_patterns:
            match = pattern.search(text)
            if match:
                flight_num = match.group(1).strip()
                # Basic validation for flight number format
                if re.match(r'^[A-Z]*\d+[A-Z]?', flight_num) or re.match(r'^[A-Z]{2}\s*\d+', flight_num):
                    return flight_num
        return None

    def determine_transport_type(self, text: str, sender_name: str = "") -> str:
        """Determine the type of transportation (train/flight/bus)"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        
        # Count indicators for each transport type
        train_score = sum(1 for p in self.compiled_transport_providers['Train'] if p.search(combined_text))
        flight_score = sum(1 for p in self.compiled_transport_providers['Flight'] if p.search(combined_text))
        bus_score = sum(1 for p in self.compiled_transport_providers['Bus'] if p.search(combined_text))
        
        # Additional scoring based on PNR format
        pnr = self.extract_pnr_number(text)
        if pnr:
            if len(pnr) == 10 and pnr.isdigit():
                train_score += 2
            elif len(pnr) == 6:
                flight_score += 2
            elif 8 <= len(pnr) <= 12:
                bus_score += 1
        
        # Check for specific service provider names (high priority)
        if any(provider in combined_text for provider in ['ambay', 'mb travels', 'madhav']):
            bus_score += 5
            
        # Check for flight-specific indicators
        if any(indicator in combined_text for indicator in ['gate', 'boarding gate', 'terminal']):
            flight_score += 3
            
        # Check for train-specific indicators
        if any(indicator in combined_text for indicator in ['platform', 'coach', 'berth']):
            train_score += 3
        
        # Return the type with highest score
        scores = {'train': train_score, 'flight': flight_score, 'bus': bus_score}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'unknown'

    def calculate_transportation_confidence_score(self, text: str, sender_name: str = "") -> int:
        """Calculate confidence score for transportation messages"""
        score = 0
        combined_text = f"{text.lower()} {sender_name.lower()}"
        
        # Check for transportation indicators
        transport_indicator_count = sum(1 for p in self.compiled_transportation_indicators if p.search(combined_text))
        score += transport_indicator_count * 8
        
        # Check if PNR is found
        if self.extract_pnr_number(text):
            score += 25
        
        # Check if date of journey is found
        if self.extract_date_of_journey(text):
            score += 20
        
        # Check if route information is found
        if self.extract_boarding_place(text) and self.extract_drop_place(text):
            score += 15
        elif self.extract_boarding_place(text) or self.extract_drop_place(text):
            score += 10
        
        # Check if transport provider is identified
        if self.extract_transport_provider(text, sender_name):
            score += 10
        
        # Check for seat and class info
        if self.extract_seat_info(text):
            score += 10
        if self.extract_class_info(text, self.determine_transport_type(text, sender_name)):
            score += 5
        
        # Check for transport-specific numbers
        transport_type = self.determine_transport_type(text, sender_name)
        if transport_type == 'bus' and self.extract_bus_number(text):
            score += 10
        elif transport_type == 'flight' and self.extract_flight_number(text):
            score += 10
        
        # Additional keywords that indicate transportation
        transport_keywords = ['booking', 'confirmation', 'ticket', 'journey', 'travel', 'platform', 'gate', 'terminal']
        keyword_matches = sum(1 for keyword in transport_keywords if keyword in combined_text)
        score += keyword_matches * 5
        
        return max(0, min(100, score))

    def is_transportation_message(self, text: str, sender_name: str = "") -> bool:
        """Check if message contains transportation-related indicators"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        
        # Primary indicators
        if any(p.search(combined_text) for p in self.compiled_transportation_indicators):
            return True
        
        # Check for PNR patterns
        if self.extract_pnr_number(text):
            return True
        
        # Check for transport providers
        for provider_type, patterns in self.compiled_transport_providers.items():
            if any(p.search(combined_text) for p in patterns):
                return True
        return False

    def parse_transportation_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse transportation information from the message"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        confidence_score = self.calculate_transportation_confidence_score(combined_text, sender_name)

        if confidence_score >= 40:  # Threshold for transportation messages
            transport_type = self.determine_transport_type(clean_message, sender_name)

            # Initialize fields
            platform_number = None
            gate_number = None
            departure_time = None
            bus_number = None
            flight_number = None

            # Extract fields based on transport type
            if transport_type == 'train':
                platform_number = self.extract_platform_number(clean_message)
            elif transport_type == 'flight':
                gate_number = self.extract_gate_number(clean_message)
                flight_number = self.extract_flight_number(clean_message)
            elif transport_type == 'bus':
                bus_number = self.extract_bus_number(clean_message)

            # Extract departure time (applicable to all)
            departure_time = self.extract_departure_time(clean_message)

            result = {
                'status': 'parsed',
                'message_type': 'transportation',
                'transport_type': transport_type,
                'confidence_score': confidence_score,
                'pnr_number': self.extract_pnr_number(clean_message),
                'date_of_journey': self.extract_date_of_journey(clean_message),
                'boarding_place': self.extract_boarding_place(clean_message),
                'drop_place': self.extract_drop_place(clean_message),
                'seat_number': self.extract_seat_info(clean_message),
                'class': self.extract_class_info(clean_message, transport_type),
                'platform_number': platform_number,
                'gate_number': gate_number,
                'departure_time': departure_time,
                'bus_number': bus_number,
                'flight_number': flight_number,
                'transport_provider': self.extract_transport_provider(clean_message, sender_name),
                'raw_message': message,
            }
            return result

        return {
            'status': 'rejected',
            'message_type': 'transportation',
            'reason': 'Message did not meet the confidence threshold for a transportation message.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    # --- FIXED OTP PARSING METHODS ---
    def extract_otp_code(self, text: str) -> Optional[str]:
        """FIXED: Enhanced OTP code extraction"""
        # FIXED: Try direct patterns first
        for pattern in self.compiled_otp_patterns:
            match = pattern.search(text)
            if match:
                otp = re.sub(r'[- ]', '', match.group(1))
                # FIXED: Validate OTP length and format
                if 4 <= len(otp) <= 8 and otp.isdigit():
                    return otp
        
        # FIXED: Fallback to true OTP patterns
        if any(p.search(text.lower()) for p in self.compiled_true_otp_patterns):
            potential_otps = re.findall(r'\b\d{4,8}\b', text)
            if potential_otps:
                return potential_otps[0]
        return None

    def extract_company_name(self, text: str, sender_name: str = "") -> Optional[str]:
        """FIXED: Enhanced company name extraction"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for company, patterns in self.compiled_company_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return company
        return None

    def calculate_otp_confidence_score(self, text: str, sender_name: str = "") -> int:
        """FIXED: Enhanced confidence score calculation for OTP messages"""
        score = 0
        text_lower = text.lower()
        combined_text = f"{text_lower} {sender_name.lower()}"
        
        # FIXED: Check for strong exclusions first
        if any(p.search(text_lower) for p in self.compiled_strong_exclusions):
            return 0
        
        # FIXED: Check for OTP code first (higher priority)
        otp_code = self.extract_otp_code(text)
        if otp_code:
            score += 50
        
        # FIXED: Check for true OTP patterns
        if any(p.search(combined_text) for p in self.compiled_true_otp_patterns):
            score += 25
        
        # FIXED: Check for company name
        if self.extract_company_name(text, sender_name):
            score += 15
        
        # FIXED: Security and validity indicators
        if any(phrase in text_lower for phrase in ["don't share", "do not share", "valid for", "expires"]):
            score += 10
        
        # FIXED: Additional OTP keywords
        otp_keywords = ['otp', 'verification', 'code', 'login', 'register']
        keyword_matches = sum(1 for keyword in otp_keywords if keyword in combined_text)
        score += keyword_matches * 5
        
        return max(0, min(100, score))

    def extract_expiry_time(self, text: str) -> Optional[Dict[str, str]]:
        """Enhanced expiry time information extraction"""
        expiry_patterns = [
            r'\bvalid\s*(?:for|within)\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bexpires?\s*in\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\b(?:otp|code)\s*.*?valid\s*(?:for|within)\s*(\d+)\s*(minutes?|mins?|min)\b',
            r'\bis\s*valid\s*within\s*(\d+)\s*(min|minutes?)\b',
        ]
        
        for pattern in expiry_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = match.group(1)
                unit = match.group(2).lower()
                
                # Normalize unit display
                normalized_unit = "min" if unit.startswith('min') else unit
                
                return {
                    'duration': duration,
                    'unit': normalized_unit,
                    'full_text': match.group(0)
                }
        return None

    # --- FIXED EMI PARSING METHODS ---
    def extract_emi_amount(self, text: str) -> Optional[str]:
        """FIXED: Enhanced EMI amount extraction including all formats"""
        for pattern in self.compiled_emi_amount_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                # Enhanced validation for reasonable EMI amounts
                try:
                    amount_float = float(amount)
                    if 100 <= amount_float <= 1000000:  # Reasonable EMI range
                        return amount
                except ValueError:
                    continue
        return None

    def extract_emi_due_date(self, text: str) -> Optional[str]:
        """Enhanced EMI due date extraction including overdue scenarios"""
        for pattern in self.compiled_emi_due_date_patterns:
            match = pattern.search(text)
            if match:
                date_str = match.group(1)
                return self.normalize_date(date_str)
        return None

    def normalize_date(self, date_str: str) -> str:
        """ENHANCED: Normalize various date formats to a standard format with better EMI date handling"""
        date_str = date_str.strip()
        
        # ENHANCED: Handle DD-Mon-YY format specifically (e.g., 05-Jul-24)
        month_abbrev_dd_match = re.match(r"(\d{1,2})[-/]([a-z]{3})[-/](\d{2,4})", date_str, re.IGNORECASE)
        if month_abbrev_dd_match:
            day = month_abbrev_dd_match.group(1).zfill(2)
            month_abbrev = month_abbrev_dd_match.group(2).title()
            year = month_abbrev_dd_match.group(3)
            if len(year) == 2:
                year = "20" + year
            return f"{day}-{month_abbrev}-{year}"
        
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
        
        # Handle YYYY-MM-DD format (ISO)
        iso_match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
        if iso_match:
            year, month, day = iso_match.groups()
            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
        
        return date_str

    def extract_bank_name(self, text: str, sender_name: str = "") -> Optional[str]:
        """Enhanced bank/lender name extraction"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for bank, patterns in self.compiled_bank_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return bank
        return None

    def extract_account_number(self, text: str) -> Optional[str]:
        """FIXED: Enhanced account number extraction"""
        text_upper = text.upper()
        for pattern in self.compiled_account_number_patterns:
            match = pattern.search(text_upper)
            if match:
                account_num = match.group(1)
                # Enhanced validation
                if any(c.isdigit() for c in account_num) and 6 <= len(account_num) <= 20:
                    # Exclude common false positives
                    if not re.match(r'^\d{4}', account_num):  # Not just 4 digits (likely year)
                        return account_num
        return None

    def calculate_emi_confidence_score(self, text: str, sender_name: str = "") -> int:
        """Enhanced confidence score calculation for EMI messages"""
        score = 0
        text_lower = text.lower()
        combined_text = f"{text_lower} {sender_name.lower()}"
        
        # Check for EMI promotion exclusions first
        if any(p.search(text_lower) for p in self.compiled_emi_exclusions):
            return 0
        
        # Check for EMI indicators
        emi_indicator_count = sum(1 for p in self.compiled_emi_indicators if p.search(combined_text))
        score += emi_indicator_count * 20
        
        # Check if EMI amount is found
        if self.extract_emi_amount(text):
            score += 30
        
        # Check if bank name is found
        if self.extract_bank_name(text, sender_name):
            score += 20
        
        # Check if account number is found
        if self.extract_account_number(text):
            score += 15
        
        # Check if due date is found
        if self.extract_emi_due_date(text):
            score += 15
        
        # Additional keywords for EMI reminders and overdue scenarios
        reminder_keywords = ['pending', 'overdue', 'bounce', 'unpaid', 'not paid', 'dishonour', 'outstanding', 'due']
        keyword_matches = sum(1 for keyword in reminder_keywords if keyword in text_lower)
        score += keyword_matches * 8
        
        return max(0, min(100, score))

    def is_emi_message(self, text: str) -> bool:
        """Check if message contains EMI-related indicators"""
        text_lower = text.lower()
        return any(p.search(text_lower) for p in self.compiled_emi_indicators)

    # --- ENHANCED: TRAFFIC CHALLAN PARSING METHODS ---
    def extract_challan_number(self, text: str) -> Optional[str]:
        """Enhanced challan number extraction"""
        text_upper = text.upper()
        for pattern in self.compiled_challan_number_patterns:
            match = pattern.search(text_upper)
            if match:
                challan_num = match.group(1)
                if self.is_valid_challan_number(challan_num):
                    return challan_num
        return None

    def is_valid_challan_number(self, challan_num: str) -> bool:
        """Enhanced validation for challan numbers"""
        challan_num = challan_num.strip()
        
        # Traditional state-based challan numbers
        if len(challan_num) >= 16 and challan_num[:2].isalpha() and challan_num[2:].isdigit():
            return True
        
        # Medium length state-based
        if 12 <= len(challan_num) <= 20 and challan_num[:2].isalpha() and challan_num[2:].isdigit():
            return True
        
        # Short numeric challans
        if 8 <= len(challan_num) <= 12 and challan_num.isdigit():
            return True
        
        # Payment reference numbers
        if 8 <= len(challan_num) <= 12 and re.match(r'^[A-Z0-9]+', challan_num):
            return True
        
        # State + alphanumeric formats
        if len(challan_num) >= 10 and re.match(r'^[A-Z]{2,6}[A-Z0-9]+', challan_num):
            return True
        
        # Generic alphanumeric format
        if len(challan_num) >= 8 and re.match(r'^[A-Z0-9]+', challan_num):
            has_letters = any(c.isalpha() for c in challan_num)
            has_numbers = any(c.isdigit() for c in challan_num)
            return has_letters and has_numbers
        
        return False

    def extract_vehicle_number(self, text: str) -> Optional[str]:
        """Enhanced vehicle number extraction"""
        text_upper = text.upper()
        for pattern in self.compiled_vehicle_number_patterns:
            match = pattern.search(text_upper)
            if match:
                vehicle_num = match.group(1)
                if self.is_valid_vehicle_number(vehicle_num):
                    return vehicle_num
        return None

    def is_valid_vehicle_number(self, vehicle_num: str) -> bool:
        """Enhanced validation for Indian vehicle number format"""
        vehicle_num = vehicle_num.replace(' ', '').upper()
        
        # Indian vehicle number formats
        patterns = [
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4}',  # Standard format
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}',  # Alternative format
        ]
        return any(re.match(pattern, vehicle_num) for pattern in patterns)

    def extract_challan_fine_amount(self, text: str) -> Optional[str]:
        """Enhanced fine amount extraction"""
        for pattern in self.compiled_challan_fine_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                try:
                    amount_float = float(amount)
                    if 1 <= amount_float <= 100000:  # Reasonable fine range
                        return amount
                except ValueError:
                    continue
        return None

    def extract_payment_link(self, text: str) -> Optional[str]:
        """Enhanced payment link extraction"""
        for pattern in self.compiled_payment_link_patterns:
            match = pattern.search(text)
            if match:
                link = match.group(1) if match.group(1) and match.group(1).startswith('http') else match.group(0)
                # Clean the link of any trailing punctuation
                link = re.sub(r'[.,;)\]}\s]*$', '', link)
                return link
        return None

    def extract_traffic_authority(self, text: str, sender_name: str = "") -> Optional[str]:
        """Enhanced traffic authority extraction"""
        combined_text = f"{text.lower()} {sender_name.lower()}"
        for authority, patterns in self.compiled_traffic_authority_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                return authority
        return None

    def determine_challan_status(self, text: str) -> str:
        """Enhanced challan status determination"""
        text_lower = text.lower()
        
        # Check for court disposal first
        for pattern in self.compiled_challan_status_patterns['court_disposal']:
            if pattern.search(text_lower):
                return 'court_disposal'
        
        # Check for payment completion status
        for pattern in self.compiled_challan_status_patterns['paid']:
            if pattern.search(text_lower):
                return 'paid'
        
        # Check for pending payment indicators
        for pattern in self.compiled_challan_status_patterns['pending']:
            if pattern.search(text_lower):
                return 'pending'
        
        # Check for issued status indicators
        for pattern in self.compiled_challan_status_patterns['issued']:
            if pattern.search(text_lower):
                return 'issued'
        
        return 'issued'

    def calculate_challan_confidence_score(self, text: str, sender_name: str = "") -> int:
        """Enhanced confidence score calculation for challan messages"""
        score = 0
        text_lower = text.lower()
        combined_text = f"{text_lower} {sender_name.lower()}"
        
        # Check for challan indicators
        challan_indicator_count = sum(1 for p in self.compiled_challan_indicators if p.search(combined_text))
        score += challan_indicator_count * 12
        
        # Check if challan number is found
        if self.extract_challan_number(text):
            score += 45
        
        # Check if vehicle number is found
        if self.extract_vehicle_number(text):
            score += 25
        
        # Check if fine amount is found
        if self.extract_challan_fine_amount(text):
            score += 20
        
        # Check if payment link is found
        if self.extract_payment_link(text):
            score += 10
        
        # Check if traffic authority is found
        if self.extract_traffic_authority(text, sender_name):
            score += 15
        
        # Enhanced keywords for different message types
        traffic_keywords = ['violation', 'traffic police', 'virtual court', 'actionable', 'disposal', 'issued against', 'found actionable']
        payment_keywords = ['payment', 'receipt', 'reference number', 'initiated', 'received', 'online lok adalat', 'sama.live']
        court_keywords = ['sent to court', 'court for disposal', 'disposal as per law']
        
        traffic_matches = sum(1 for keyword in traffic_keywords if keyword in text_lower)
        payment_matches = sum(1 for keyword in payment_keywords if keyword in text_lower)
        court_matches = sum(1 for keyword in court_keywords if keyword in text_lower)
        
        score += traffic_matches * 8
        score += payment_matches * 8
        score += court_matches * 10  # Higher weight for court disposal
        
        # Boost score for specific platforms
        if any(keyword in text_lower for keyword in ['ifms', 'mptreasury', 'successfully done', 'sama.live', 'online lok adalat']):
            score += 15
        
        return max(0, min(100, score))

    def is_challan_message(self, text: str) -> bool:
        """Enhanced challan message detection"""
        text_lower = text.lower()
        
        # Primary indicators
        if any(p.search(text_lower) for p in self.compiled_challan_indicators):
            return True
        
        # Secondary indicators
        secondary_patterns = [
            r'reference\s*number.*payment',
            r'challan.*receipt',
            r'traffic.*payment',
            r'violation.*amount',
            r'issued\s*against',
            r'online\s*lok\s*adalat',
            r'sent\s*to\s*court',
            r'court\s*for\s*disposal',
        ]
        return any(re.search(pattern, text_lower) for pattern in secondary_patterns)

    def parse_challan_message(self, message: str, sender_name: str = "") -> Dict:
        """Enhanced challan information parsing"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        confidence_score = self.calculate_challan_confidence_score(combined_text, sender_name)
        
        if confidence_score >= 40:
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
        """Enhanced EMI information parsing"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        confidence_score = self.calculate_emi_confidence_score(combined_text, sender_name)
        
        if confidence_score >= 50:
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

    # --- NEW: EPF PARSING METHODS ---
    def extract_uan_number(self, text: str) -> Optional[str]:
        """Extract UAN number from EPF messages"""
        for pattern in self.compiled_uan_patterns:
            match = pattern.search(text)
            if match:
                uan = match.group(1)
                if len(uan) == 12 and uan.isdigit():
                    return uan
        return None

    def extract_epf_amount(self, text: str) -> Optional[str]:
        """Extract amount from EPF messages"""
        # First, try specific EPF amount patterns
        for pattern in self.compiled_epf_amount_patterns:
            match = pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                try:
                    if float(amount) > 0:
                        return amount
                except (ValueError, IndexError):
                    continue
        
        # Fallback for generic bank credit messages with EPF context
        if any(ind in text.lower() for ind in ['epf', 'epfo']):
            generic_credit_pattern = re.compile(r'rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*credited', re.IGNORECASE)
            match = generic_credit_pattern.search(text)
            if match:
                amount = match.group(1).replace(',', '')
                try:
                    if float(amount) > 0:
                        return amount
                except (ValueError, IndexError):
                    pass
        return None

    def extract_available_balance(self, text: str) -> Optional[str]:
        """Extract available balance from bank-related EPF messages"""
        for pattern in self.compiled_available_balance_patterns:
            match = pattern.search(text)
            if match:
                balance = match.group(1).replace(',', '')
                try:
                    if float(balance) >= 0:
                        return balance
                except (ValueError, IndexError):
                    continue
        return None

    def calculate_epf_confidence_score(self, text: str, sender_name: str = "") -> int:
        """Calculate confidence score for EPF messages"""
        score = 0
        text_lower = text.lower()
        combined_text = f"{text_lower} {sender_name.lower()}"
        
        # Check for strong indicators
        epf_indicator_count = sum(1 for p in self.compiled_epf_indicators if p.search(combined_text))
        score += epf_indicator_count * 25
        
        # Check if UAN is found (very strong indicator)
        if self.extract_uan_number(text):
            score += 50
        
        # Check if amount is found
        if self.extract_epf_amount(text):
            score += 20
        
        # Check for specific keywords
        if 'contribution' in text_lower:
            score += 15
        if 'auto claim' in text_lower or 'transfer' in text_lower:
            score += 15 # Transfer messages are also important
        if 'passbook' in text_lower:
            score += 10
        
        # Boost score for "EPFO" sender
        if 'epfo' in sender_name.lower():
            score += 30
            
        return max(0, min(100, score))

    def parse_epf_message(self, message: str, sender_name: str = "") -> Dict:
        """Parse EPF contribution and transfer information"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        confidence_score = self.calculate_epf_confidence_score(combined_text, sender_name)
        
        if confidence_score >= 40:
            result = {
                'status': 'parsed',
                'message_type': 'epf',
                'confidence_score': confidence_score,
                'amount_credited': self.extract_epf_amount(clean_message),
                'available_balance': self.extract_available_balance(clean_message),
                'uan_number': self.extract_uan_number(clean_message),
                'account_number': self.extract_account_number(clean_message),
                'raw_message': message,
            }
            return result
        
        return {
            'status': 'rejected',
            'message_type': 'epf',
            'reason': 'Message did not meet the confidence threshold for an EPF message.',
            'confidence_score': confidence_score,
            'message_preview': clean_message[:100],
        }

    def parse_single_message(self, message: str, sender_name: str = "", message_type: str = "auto") -> Dict:
        """FIXED: Enhanced single message parsing with better auto-detection"""
        clean_message = self.clean_text(message)
        
        if message_type == "auto":
            # FIXED: Enhanced auto-detection logic with better prioritization
            
            # First check for OTP indicators (most specific)
            otp_score = self.calculate_otp_confidence_score(clean_message, sender_name)
            if otp_score >= 50 and self.extract_otp_code(clean_message):
                return self.parse_otp_message(message, sender_name)

            # Then check for EPF (EPFO/UAN are strong indicators)
            epf_score = self.calculate_epf_confidence_score(clean_message, sender_name)
            if epf_score >= 40:
                return self.parse_epf_message(message, sender_name)
            
            # Then check for transportation (PNR is a strong indicator)
            if self.extract_pnr_number(clean_message):
                return self.parse_transportation_message(message, sender_name)
            
            # Count specific indicators
            challan_indicators = sum(1 for p in self.compiled_challan_indicators if p.search(clean_message.lower()))
            emi_indicators = sum(1 for p in self.compiled_emi_indicators if p.search(clean_message.lower()))
            transport_indicators = sum(1 for p in self.compiled_transportation_indicators if p.search(clean_message.lower()))
            
            # Check for specific patterns that are strong indicators
            if (challan_indicators > 0 or 
                self.extract_challan_number(clean_message) or 
                self.extract_vehicle_number(clean_message)):
                return self.parse_challan_message(message, sender_name)
            
            if (emi_indicators > 0 and 
                not any(p.search(clean_message.lower()) for p in self.compiled_emi_exclusions)):
                return self.parse_emi_message(message, sender_name)
            
            if transport_indicators > 0:
                return self.parse_transportation_message(message, sender_name)
            
            # Fallback to OTP if nothing else matches
            return self.parse_otp_message(message, sender_name)
            
        elif message_type == "transportation":
            return self.parse_transportation_message(message, sender_name)
        elif message_type == "challan":
            return self.parse_challan_message(message, sender_name)
        elif message_type == "emi":
            return self.parse_emi_message(message, sender_name)
        elif message_type == "otp":
            return self.parse_otp_message(message, sender_name)
        elif message_type == "epf":
            return self.parse_epf_message(message, sender_name)
        else:
            return {'status': 'error', 'reason': 'Invalid message type specified'}

    def parse_otp_message(self, message: str, sender_name: str = "") -> Dict:
        """FIXED: Enhanced OTP information parsing"""
        clean_message = self.clean_text(message)
        combined_text = f"{clean_message} {sender_name}"
        confidence_score = self.calculate_otp_confidence_score(combined_text, sender_name)
        
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

    # --- EXISTING OTP HELPER METHODS ---
    def extract_purpose(self, text: str) -> Optional[str]:
        """Extract purpose of OTP"""
        purpose_patterns = {
            'Registration': [r'\b(?:registration|sign\s*up)\b'],
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

    def extract_security_warnings(self, text: str) -> List[str]:
        """Extract security warnings"""
        security_patterns = [r'\bdo\s*not\s*share\b', r'\bnever\s*share\b']
        warnings = []
        for pattern in security_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                warnings.append(match.group(0))
        return warnings

    # --- REMAINING METHODS (process_csv_file, summary stats, etc.) ---
    def process_csv_file(self, input_file: str, output_file: str = None, message_type: str = "auto") -> Dict:
        """Process CSV file for all message types"""
        print("Enhanced Message Parser v12.0 - EPF ADDED - Analyzing Messages")
        print("=" * 90)
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
        print(f"Analysis completed in {parse_time/60:.1f} minutes")
        
        # Separate messages by type
        otp_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'otp']
        emi_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'emi']
        challan_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'challan']
        transportation_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'transportation']
        epf_messages = [msg for msg in parsed_messages if msg.get('message_type') == 'epf'] # NEW
        
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'total_parsed_messages': len(parsed_messages),
                'otp_messages_found': len(otp_messages),
                'emi_messages_found': len(emi_messages),
                'challan_messages_found': len(challan_messages),
                'transportation_messages_found': len(transportation_messages),
                'epf_messages_found': len(epf_messages), # NEW
                'rejected_messages': len(rejected_messages),
                'detection_rate': round((len(parsed_messages) / total_messages) * 100, 2),
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '12.0_epf_added'
            },
            'summary_statistics': {
                'otp_stats': self.generate_otp_summary_stats(otp_messages),
                'emi_stats': self.generate_emi_summary_stats(emi_messages),
                'challan_stats': self.generate_challan_summary_stats(challan_messages),
                'transportation_stats': self.generate_transportation_summary_stats(transportation_messages),
                'epf_stats': self.generate_epf_summary_stats(epf_messages) # NEW
            },
            'otp_messages': otp_messages,
            'emi_messages': emi_messages,
            'challan_messages': challan_messages,
            'transportation_messages': transportation_messages,
            'epf_messages': epf_messages, # NEW
            'sample_rejected_messages': rejected_messages[:10]
        }
        
        self.display_parsing_summary(results)
        
        if output_file is None:
            base_name = input_file.replace('.csv', '')
            output_file = f"{base_name}_parsed_messages_epf.json"
        
        print(f"Saving results to: {output_file}")
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
        """Generate summary statistics for traffic challan messages"""
        if not challan_messages:
            return {}
        
        # Authority distribution
        authorities = [msg.get('traffic_authority') for msg in challan_messages if msg.get('traffic_authority')]
        authority_counts = {}
        for authority in authorities:
            authority_counts[authority] = authority_counts.get(authority, 0) + 1
        
        # Status distribution - Enhanced with court disposal
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

    def generate_transportation_summary_stats(self, transportation_messages: List[Dict]) -> Dict:
        """Generate summary statistics for transportation messages"""
        if not transportation_messages:
            return {}
        
        # Transport type distribution
        transport_types = [msg.get('transport_type') for msg in transportation_messages if msg.get('transport_type')]
        type_counts = {}
        for transport_type in transport_types:
            type_counts[transport_type] = type_counts.get(transport_type, 0) + 1
        
        # Provider distribution
        providers = [msg.get('transport_provider') for msg in transportation_messages if msg.get('transport_provider')]
        provider_counts = {}
        for provider in providers:
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Route analysis
        boarding_places = [msg.get('boarding_place') for msg in transportation_messages if msg.get('boarding_place')]
        boarding_counts = {}
        for place in boarding_places:
            boarding_counts[place] = boarding_counts.get(place, 0) + 1
        
        drop_places = [msg.get('drop_place') for msg in transportation_messages if msg.get('drop_place')]
        drop_counts = {}
        for place in drop_places:
            drop_counts[place] = drop_counts.get(place, 0) + 1
        
        confidence_scores = [msg.get('confidence_score', 0) for msg in transportation_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            'total_count': len(transportation_messages),
            'distributions': {
                'transport_types': dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)),
                'top_providers': dict(sorted(provider_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'top_boarding_places': dict(sorted(boarding_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'top_drop_places': dict(sorted(drop_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            },
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
                'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
                'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
                'messages_with_pnr': sum(1 for msg in transportation_messages if msg.get('pnr_number')),
                'messages_with_doj': sum(1 for msg in transportation_messages if msg.get('date_of_journey')),
                'messages_with_boarding_place': sum(1 for msg in transportation_messages if msg.get('boarding_place')),
                'messages_with_drop_place': sum(1 for msg in transportation_messages if msg.get('drop_place')),
                'messages_with_provider': sum(1 for msg in transportation_messages if msg.get('transport_provider')),
                'messages_with_departure_time': sum(1 for msg in transportation_messages if msg.get('departure_time')),
                'messages_with_bus_number': sum(1 for msg in transportation_messages if msg.get('bus_number')),
                'messages_with_flight_number': sum(1 for msg in transportation_messages if msg.get('flight_number')),
            }
        }

    # NEW: EPF summary statistics
    def generate_epf_summary_stats(self, epf_messages: List[Dict]) -> Dict:
        """Generate summary statistics for EPF messages"""
        if not epf_messages:
            return {}
        
        # Analyze amounts
        amounts = []
        for msg in epf_messages:
            amount_str = msg.get('amount_credited')
            if amount_str:
                try:
                    amount = float(amount_str.replace(',', ''))
                    amounts.append(amount)
                except ValueError:
                    continue
        
        confidence_scores = [msg.get('confidence_score', 0) for msg in epf_messages]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        amount_stats = {}
        if amounts:
            amount_stats = {
                'average_amount': round(sum(amounts) / len(amounts), 2),
                'min_amount': min(amounts),
                'max_amount': max(amounts),
                'total_value': sum(amounts)
            }
            
        return {
            'total_count': len(epf_messages),
            'amount_statistics': amount_stats,
            'quality_metrics': {
                'average_confidence_score': round(avg_confidence, 2),
                'messages_with_amount': sum(1 for msg in epf_messages if msg.get('amount_credited')),
                'messages_with_uan': sum(1 for msg in epf_messages if msg.get('uan_number')),
                'messages_with_balance': sum(1 for msg in epf_messages if msg.get('available_balance')),
            }
        }

    def display_parsing_summary(self, results: Dict):
        """Display comprehensive parsing summary"""
        metadata = results['metadata']
        otp_stats = results.get('summary_statistics', {}).get('otp_stats', {})
        emi_stats = results.get('summary_statistics', {}).get('emi_stats', {})
        challan_stats = results.get('summary_statistics', {}).get('challan_stats', {})
        transportation_stats = results.get('summary_statistics', {}).get('transportation_stats', {})
        epf_stats = results.get('summary_statistics', {}).get('epf_stats', {}) # NEW
        
        print("" + "="*90)
        print("ENHANCED MESSAGE PARSING RESULTS SUMMARY v12.0 (EPF ADDED)")
        print("="*90)
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"Total Parsed Messages: {metadata['total_parsed_messages']:,}")
        print(f"  - OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"  - EMI Messages Found: {metadata['emi_messages_found']:,}")
        print(f"  - Challan Messages Found: {metadata['challan_messages_found']:,}")
        print(f"  - Transportation Messages Found: {metadata['transportation_messages_found']:,}")
        print(f"  - EPF Messages Found: {metadata['epf_messages_found']:,}") # NEW
        print(f"Messages Rejected: {metadata['rejected_messages']:,}")
        print(f"Overall Detection Rate: {metadata['detection_rate']}%")
        
        # Display detailed summaries for each type
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
            print(f"Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")
        
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
                print(f"Average EMI: Rs.{amount_stats.get('average_amount', 0):,.2f}")
            print(f"Data Completeness: {quality_metrics.get('messages_with_amount', 0)}/{emi_stats['total_count']} have amounts")
        
        if challan_stats and challan_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("TRAFFIC CHALLAN MESSAGES SUMMARY")
            print("="*60)
            distributions = challan_stats.get('distributions', {})
            print("Challan Status Distribution:")
            for status, count in distributions.get('status_types', {}).items():
                percentage = (count / challan_stats['total_count']) * 100
                status_display = {
                    'paid': 'Payment Confirmed',
                    'pending': 'Payment Pending', 
                    'issued': 'Newly Issued',
                    'court_disposal': 'Sent to Court'
                }.get(status, status.title())
                print(f"  {status_display}: {count:,} ({percentage:.1f}%)")
        
        if transportation_stats and transportation_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("TRANSPORTATION MESSAGES SUMMARY")
            print("="*60)
            distributions = transportation_stats.get('distributions', {})
            quality_metrics = transportation_stats.get('quality_metrics', {})
            print("Transportation Types:")
            for transport_type, count in distributions.get('transport_types', {}).items():
                percentage = (count / transportation_stats['total_count']) * 100
                print(f"  {transport_type.title()}: {count:,} ({percentage:.1f}%)")
            print("Data Completeness:")
            print(f"  PNR: {quality_metrics.get('messages_with_pnr', 0)}/{transportation_stats['total_count']}")
            print(f"  Boarding/Drop: {quality_metrics.get('messages_with_boarding_place', 0)}/{quality_metrics.get('messages_with_drop_place', 0)}")
            print(f"  Bus Numbers: {quality_metrics.get('messages_with_bus_number', 0)}")
            print(f"  Flight Numbers: {quality_metrics.get('messages_with_flight_number', 0)}")
            
        # NEW: Display EPF Summary
        if epf_stats and epf_stats.get('total_count', 0) > 0:
            print("\n" + "="*60)
            print("EPF MESSAGES SUMMARY")
            print("="*60)
            quality_metrics = epf_stats.get('quality_metrics', {})
            amount_stats = epf_stats.get('amount_statistics', {})
            if amount_stats:
                print(f"Average Amount Credited: Rs.{amount_stats.get('average_amount', 0):,.2f}")
            print(f"Data Completeness:")
            print(f"  UAN Found: {quality_metrics.get('messages_with_uan', 0)}/{epf_stats['total_count']}")
            print(f"  Amount Found: {quality_metrics.get('messages_with_amount', 0)}/{epf_stats['total_count']}")

    def interactive_message_analyzer(self):
        """Interactive analyzer for all message types"""
        print("Interactive Message Analyzer v12.0 (EPF ADDED)")
        print("=" * 70)
        print("Parsing for OTP, EMI, Challan, Transportation & EPF messages")
        print("Enter messages to analyze (type 'quit' to exit)")
        
        while True:
            print("\n" + "-" * 70)
            message = input("Enter message: ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                break
            
            if not message:
                continue
            
            sender = input("Enter sender name (optional): ").strip()
            message_type = input("Message type (otp/emi/challan/transportation/epf/auto) [auto]: ").strip().lower()
            
            if not message_type:
                message_type = "auto"
            
            print("Detailed Analysis:")
            print("-" * 40)
            result = self.parse_single_message(message, sender, message_type)
            
            print(f"Message Type: {result.get('message_type', 'Unknown')}")
            print(f"Confidence Score: {result.get('confidence_score', 0)}%")
            print(f"Final Status: {result['status']}")
            
            if result['status'] == 'parsed':
                if result['message_type'] == 'otp':
                    print(f"OTP Code: {result.get('otp_code')}")
                    print(f"Company: {result.get('company_name')}")
                    expiry = result.get('expiry_info')
                    if expiry:
                        print(f"Validity: {expiry.get('duration')} {expiry.get('unit')}")
                elif result['message_type'] == 'emi':
                    print(f"EMI Amount: Rs.{result.get('emi_amount')}")
                    print(f"Due Date: {result.get('emi_due_date')}")
                    print(f"Bank: {result.get('bank_name')}")
                    print(f"Account: {result.get('account_number')}")
                elif result['message_type'] == 'challan':
                    print(f"Challan Number: {result.get('challan_number')}")
                    print(f"Vehicle Number: {result.get('vehicle_number')}")
                    print(f"Fine Amount: Rs.{result.get('fine_amount')}")
                    print(f"Status: {result.get('challan_status')}")
                elif result['message_type'] == 'transportation':
                    print(f"Transport Type: {result.get('transport_type')}")
                    print(f"PNR Number: {result.get('pnr_number')}")
                    print(f"Boarding Place: {result.get('boarding_place')}")
                    print(f"Drop Place: {result.get('drop_place')}")
                    print(f"Bus Number: {result.get('bus_number')}")
                    print(f"Flight Number: {result.get('flight_number')}")
                    print(f"Seat Info: {result.get('seat_number')}")
                    print(f"Gate/Platform: {result.get('gate_number') or result.get('platform_number')}")
                elif result['message_type'] == 'epf':
                    print(f"Amount Credited: Rs.{result.get('amount_credited')}")
                    print(f"Available Balance: Rs.{result.get('available_balance')}")
                    print(f"UAN Number: {result.get('uan_number')}")
                    print(f"Account Number: {result.get('account_number')}")
            else:
                print(f"Rejection Reason: {result.get('reason')}")

# Example usage
if __name__ == "__main__":
    parser = EnhancedMessageParser()
    
    # Test the fixed examples
    print("Testing EPF parsing with examples:")
    print("="*70)
    
    # Test EPF contribution message
    epf_test_1 = "Dear Member, EPF Contribution of Rs. 1321 against UAN 101206072844 for due month 062019 has been received. Passbook will be updated shortly. Regards EPFO"
    result = parser.parse_single_message(epf_test_1, "EPFO", "auto")
    print(f"\nEPF Contribution Test Result:")
    print(json.dumps(result, indent=2))
    
    # Test EPF transfer message
    epf_test_2 = "Auto claim to transfer your EPF accumulations from VIRAJ MANPOWER SERVICES to VIRAJ MANPOWER SERVICES has been considered against UAN 101174226149."
    result = parser.parse_single_message(epf_test_2, "EPFO", "auto")
    print(f"\nEPF Transfer Test Result:")
    print(json.dumps(result, indent=2))
    
    # Test Bank credit for EPF
    epf_test_3 = "BOI -  Rs 1053.00 Credited(TRF)EPF MONTHLY JUL24 M143 in your Ac XX9122 on 31-07-2024. .Avl BalRs 6610.16"
    result = parser.parse_single_message(epf_test_3, "BOI", "auto")
    print(f"\nEPF Bank Credit Test Result:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*70)
    print("EPF Parser added in version 12.0!")
    print("="*70)