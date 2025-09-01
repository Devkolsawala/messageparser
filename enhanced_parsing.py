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
            r'\b(\d{3}[- ]?\d{3})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code)',
            r'enter\s*(\d{4,8})\s*to',
            r'\b(\d{4,8})\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password|verification\s*code)',
            r'g-(\d{6})\b'
        ]
        # --- EMI Amount Extraction Patterns ---
        self.emi_amount_patterns = [
            r'emi\s*(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'emi\s*(?:amount\s*)?(?:is\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:loan\s*)?emi\s*(?:amount\s*)?(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'(?:payment\s*)?(?:of\s*)?rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)[/-]*\s*(?:for|is)\s*(?:your\s*)?(?:loan\s*)?emi',
            r'emi\s*rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'amount\s*(?:is\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d{1,2})?)[,\s]*(?:emi|loan)'
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
            r'challan\s*([A-Z]{2}\d{10,20})\s*issued'
        ]
        self.vehicle_number_patterns = [
            r'vehicle\s*no\.?\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'vehicle\s*(?:number\s*)?[:\s]*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'against\s*your\s*vehicle\s*(?:number\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'for\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'by\s*your\s*vehicle\s*(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'vehicle\s*(?:registration\s*)?(?:no\.?\s*)?([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'issued\s*against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})',
            r'against\s*([A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4})'
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
        # --- DEBUGGED & ENHANCED: TRANSPORTATION MESSAGE PARSING PATTERNS ---
        # PNR Patterns for different transportation modes
        self.pnr_patterns = [
            # Train PNRs (10 digits)
            r'pnr\s*[:\-]?\s*(\d{10})\b',
            r'pnr\s*(?:number|no)?\s*[:\-]?\s*(\d{10})\b',
            # Flight PNRs (6 characters alphanumeric)
            r'pnr\s*(?:is\s*)?([A-Z0-9]{6})\s*[-\s]',
            r'(?:your\s*)?(?:indigo\s*)?pnr\s*(?:is\s*)?([A-Z0-9]{6})\b',
            # Bus PNRs (variable format)
            r'bus\s*pnr\s*[:\-]?\s*([A-Z0-9]{8,12})\b',
            r'pnr\s*[:\-]?\s*([A-Z]\d{9})\b',
            # Generic PNR patterns
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
            # Flight specific date formats
            r'(\d{1,2}[a-z]{3})\b',
            r'(\d{1,2}\s*[a-z]{3,9}\s*\d{2,4})',
            # Bus specific date-time formats
            r'doj:\s*(\d{1,2}[-/][a-z]{3}[-/]\d{4}\s*\d{2}:\d{2})',
            # Handle DD-Mon-YY format from various keywords
            r'(?:\bdoj|boardingdate)\s*[:\-]?\s*(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b',
        ]
        # DEBUGGED: More specific route patterns to avoid capturing extra words
        self.route_patterns = [
            # High-priority patterns for station/airport codes
            r'(?:frm|from)\s+([A-Z]{2,5})\s+to\s+([A-Z]{2,5})\b',
            r'\b([A-Z]{2,5})[-\s]([A-Z]{2,5})\b',
            # Flight routes (airport codes)
            r'([A-Z]{3})\(T\d?\)[-\s]*([A-Z]{3})',
            r'([A-Z]{3})[-\s]([A-Z]{3})\s*\d{4}[-\s]\d{4}',
            # Bus routes (less prone to errors)
            r'route\s*[:\-]?\s*([A-Z\s]{3,20})\s*[-to]\s*([A-Z\s]{3,20})',
        ]
        # DEBUGGED: Using specific keywords and formats to prevent incorrect matches
        self.boarding_place_patterns = [
            r'boarding\s*(?:station|point)?\s*(?:is|:)?\s*([a-zA-Z\s\d]+?)\s*-\s*([A-Z]{3,5})',
            r'boarding\s*(?:at|from|:)\s*([a-zA-Z\s,]+?)(?:\s*at\s*\d{2}:\d{2})',
        ]
        self.drop_place_patterns = [
            r'destination\s*(?:station|point)?\s*(?:is|:)?\s*([a-zA-Z\s\d]+?)\s*-\s*([A-Z]{3,5})',
            r'arrival\s*at\s*([a-zA-Z\s,]+)',
        ]
        # DEBUGGED & ENHANCED: Seat and Class Information Patterns to capture more formats
        # IMPROVED: Patterns to avoid trailing commas/punctuation
        self.seat_patterns = [
            # CNF/D3/76
            r'\b(?:CNF|WL|RAC)/([A-Z0-9]+)/([\d,\s&]+)\b',
            # P1-D4,31 (NEW)
            r'P\d[-]([A-Z0-9]+)[,]([\d,\s&]+)\b',
            # , D4 31 (NEW) - Capture after a comma, more restrictive
            r',\s*([A-Z0-9]{1,4})\s+([\d,\s&]+)\b',
            # D4,31 (NEW) - Simple pair, more restrictive
            r'\b([A-Z0-9]{1,4})[,]\s*([\d]+)\b',
            # Coach: S5, Berth: 34
            r'(?:coach|trn)\s*[:\-]?\s*([A-Z0-9]+)\s*[,]\s*(?:berth|seat)\s*[:\-]?\s*([\d,\s&]+)\b',
            # S5, 34, SL (NEW) - Extract coach and seat, class handled separately
            r'\b([A-Z]+\d+)\s*[,]\s*([\d,\s]+)[,]\s*(?:SL|3A|2A|1A|CC|2S)\b',
            # Seat No: 14F, 14G
            r'seat\s*(?:no\.?|nos\.?)?[:\s]*([A-Z0-9,\s]+)\b',
            # Berth: 23 UB
            r'berth\s*[:\-]?\s*([A-Z0-9,\s]+)\b',
        ]

        # IMPROVED: Class patterns to be more specific and avoid false positives
        self.class_patterns = [
            # Explicitly look for class abbreviations like 2S, SL, etc. with boundaries
            r'\b(2S)\b',
            r'\b(SL|3A|2A|1A|CC)\b',
            # Look for "CL - SLEEPER CLASS", "Cls:2S" etc.
            r'(?:class|cl|cls)\s*[:\-]?\s*([A-Z\s/]+)\b',
            # Full names
            r'\b(Sleeper|AC\s*3\s*Tier|AC\s*2\s*Tier|AC\s*First\s*Class|AC\s*Chair\s*Car)\b',
            r'\b(Economy|Business|First\s*Class)\b',
            r'\b(A/C\s*Sleeper|Non\s*A/C\s*Seater)\b'
        ]

        # NEW: Patterns for Platform and Gate Numbers
        self.platform_patterns = [
            r'\b(?:platform|plat|pf)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z]?\d{1,2})\b'
        ]
        self.gate_patterns = [
            r'\b(?:gate|boarding\s*gate)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9]+)\b'
        ]

        # NEW: Pattern for Departure Time (DP, Departure)
        self.departure_time_patterns = [
            r'dp\s*[:\-]?\s*(\d{1,2}:\d{2})',
            r'departure\s*[:\-]?\s*(\d{1,2}:\d{2})',
            r'boarding\s*at\s*(\d{1,2}:\d{2})',
            r'(\d{2}:\d{2})[-\s](?:\d{2}:\d{2})\s*hrs?',
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
                r'flight\s*\d+[A-Z]', r'\d+[A-Z]\s*\d+', r'web\s*check[-\s]in',
                r'terminal\s*[T]?\d', r'departure.*arrival', r'boarding'
            ],
            'Bus': [
                r'\bksrtc\b', r'\bmsrtc\b', r'\btsrtc\b', r'\bapsrtc\b',
                r'\brstc\b', r'\bupsrtc\b', r'\bmksrtc\b',
                r'bus\s*no\s*[:\-]?\s*[A-Z0-9]+', r'crew\s*mobile',
                r'happy\s*journey', r'bus\s*pnr',
                # Specific bus operators
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
            r'(\d{4,8})\s*is\s*your'
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
        # NEW: Compile departure time patterns
        self.compiled_departure_time_patterns = [re.compile(p, re.IGNORECASE) for p in self.departure_time_patterns]

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
        if len(pnr) == 6 and re.match(r'^[A-Z0-9]+$', pnr):
            return True
        # Bus PNR: Variable format (8-12 characters)
        if 8 <= len(pnr) <= 12 and re.match(r'^[A-Z0-9]+$', pnr):
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
            # Attempt to parse with day, abbreviated month, and 2-digit year
            dt_obj = datetime.strptime(date_str, '%d-%b-%y')
            return dt_obj.strftime('%d-%m-%Y')
        except ValueError:
            pass # Continue to other formats if this one fails
        # Handle formats like 14Nov
        if re.match(r'^\d{1,2}[a-z]{3}$', date_str, re.IGNORECASE):
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
            return datetime_match.group(0)  # Return full datetime
        return date_str

    def extract_boarding_place(self, text: str) -> Optional[str]:
        """DEBUGGED: Extract boarding place with higher precision"""
        # First, try high-precision route patterns for codes
        for pattern in self.compiled_route_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        # Then, try patterns with keywords like "boarding"
        for pattern in self.compiled_boarding_place_patterns:
            match = pattern.search(text)
            if match:
                # Group 2 is usually the code, group 1 is the full name. Prioritize code.
                return (match.group(2) or match.group(1)).strip()
        return None

    def extract_drop_place(self, text: str) -> Optional[str]:
        """DEBUGGED: Extract drop place with higher precision"""
        # First, try high-precision route patterns for codes
        for pattern in self.compiled_route_patterns:
            match = pattern.search(text)
            if match and match.lastindex >= 2:
                return match.group(2).strip()
        # Then, try patterns with keywords like "destination"
        for pattern in self.compiled_drop_place_patterns:
            match = pattern.search(text)
            if match:
                 # Group 2 is usually the code, group 1 is the full name. Prioritize code.
                return (match.group(2) or match.group(1)).strip()
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
                    # Check for specific bus operators mentioned in the new patterns
                    if 'ambay' in combined_text:
                        return 'Ambay Travels'
                    elif 'mb travels' in combined_text:
                        return 'M B Travels'
                    elif 'madhav' in combined_text:
                        return 'Madhav Travels'
                    elif 'sanjeev' in combined_text:
                        return 'Sanjeev Travels'
                    elif 'shree' in combined_text:
                        return 'Shree Travels'
                    return 'Bus Service'
        return None

    def extract_seat_info(self, text: str) -> Optional[str]:
        """DEBUGGED & ENHANCED: Extract seat, coach, and berth information, cleaning punctuation."""
        # Create a list to store all seat numbers found
        all_seats = []
        
        # Search for seat patterns across the entire text
        for pattern in self.compiled_seat_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                # Extract groups and clean them
                groups = [group.strip().rstrip('.,;') for group in match.groups() if group]
                # Add the cleaned seat info to our list
                all_seats.extend(groups)
        
        # If we found any seats, join them with a comma and space
        if all_seats:
            return ", ".join(all_seats)
        return None

    def extract_class_info(self, text: str, transport_type: str) -> Optional[str]:
        """IMPROVED: Extract and normalize travel class information, only if explicitly found."""
        # Find all potential matches
        potential_matches = []
        for pattern in self.compiled_class_patterns:
            match = pattern.search(text)
            if match:
                potential_matches.append(match.group(1).upper().strip())

        # If no explicit class found, return None
        if not potential_matches:
             return None # Return None instead of "Not Specified"

        # Prioritize based on specificity or order if needed (take the first match)
        class_info = potential_matches[0] # Take the first (often most specific) match

        if transport_type == 'train':
            # Map abbreviations to full names if it's a known abbreviation
            return self.train_class_map.get(class_info, class_info.title())
        return class_info.title()

    def extract_platform_number(self, text: str) -> Optional[str]:
        """NEW: Extract platform number for train messages."""
        for pattern in self.compiled_platform_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip().upper()
        return None

    def extract_gate_number(self, text: str) -> Optional[str]:
        """NEW: Extract gate number for flight messages."""
        for pattern in self.compiled_gate_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip().upper()
        return None

    def extract_departure_time(self, text: str) -> Optional[str]:
        """NEW: Extract departure time from the message."""
        for pattern in self.compiled_departure_time_patterns:
            match = pattern.search(text)
            if match:
                time_str = match.group(1).strip()
                # Basic validation: check if it looks like HH:MM
                if re.match(r'^\d{1,2}:\d{2}$', time_str):
                    return time_str
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
        if 'ambay' in combined_text or 'mb travels' in combined_text or 'madhav' in combined_text:
            bus_score += 5
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

            # Initialize new fields
            platform_number = None
            gate_number = None
            departure_time = None # Initialize new field

            # Extract new fields based on transport type
            if transport_type == 'train':
                platform_number = self.extract_platform_number(clean_message)
            elif transport_type == 'flight':
                gate_number = self.extract_gate_number(clean_message)

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
                'class': self.extract_class_info(clean_message, transport_type), # Pass transport_type
                'platform_number': platform_number,
                'gate_number': gate_number,
                'departure_time': departure_time, # Add new field to result
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
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4}',  # HR87K5231, DL10SS4997, HR51BM6192, GJ05RK8881
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}',  # GJ05CX0282
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
        score += challan_indicator_count * 12
        # Check if challan number is found - Higher weight for stronger identifier
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
        if self.extract_traffic_authority(text):
            score += 15
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
        """Parse a single message for OTP, EMI, challan, or transportation content - Enhanced"""
        clean_message = self.clean_text(message)
        if message_type == "auto":
            # Auto-detect message type based on content with enhanced logic
            challan_indicators = sum(1 for p in self.compiled_challan_indicators if p.search(clean_message.lower()))
            emi_indicators = sum(1 for p in self.compiled_emi_indicators if p.search(clean_message.lower()))
            transport_indicators = sum(1 for p in self.compiled_transportation_indicators if p.search(clean_message.lower()))
            # Enhanced auto-detection logic with transportation
            if transport_indicators > 0 or self.extract_pnr_number(clean_message):
                return self.parse_transportation_message(message, sender_name)
            elif challan_indicators > 0 or self.extract_challan_number(clean_message) or self.extract_vehicle_number(clean_message):
                return self.parse_challan_message(message, sender_name)
            elif emi_indicators > 0 and not any(p.search(clean_message.lower()) for p in self.compiled_emi_exclusions):
                return self.parse_emi_message(message, sender_name)
            else:
                return self.parse_otp_message(message, sender_name)
        elif message_type == "transportation":
            return self.parse_transportation_message(message, sender_name)
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
        """Process CSV file for OTP, EMI, challan, and transportation messages"""
        print("Enhanced Message Parser v9.3 - Analyzing Messages for OTP, EMI, Traffic Challan, and Transportation Content")
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
        results = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_input_messages': int(total_messages),
                'total_parsed_messages': len(parsed_messages),
                'otp_messages_found': len(otp_messages),
                'emi_messages_found': len(emi_messages),
                'challan_messages_found': len(challan_messages),
                'transportation_messages_found': len(transportation_messages),
                'rejected_messages': len(rejected_messages),
                'detection_rate': round((len(parsed_messages) / total_messages) * 100, 2),
                'processing_time_minutes': round(parse_time / 60, 2),
                'parser_version': '9.3_debugged_transportation'
            },
            'summary_statistics': {
                'otp_stats': self.generate_otp_summary_stats(otp_messages),
                'emi_stats': self.generate_emi_summary_stats(emi_messages),
                'challan_stats': self.generate_challan_summary_stats(challan_messages),
                'transportation_stats': self.generate_transportation_summary_stats(transportation_messages)
            },
            'otp_messages': otp_messages,
            'emi_messages': emi_messages,
            'challan_messages': challan_messages,
            'transportation_messages': transportation_messages,
            'sample_rejected_messages': rejected_messages[:10]
        }
        self.display_parsing_summary(results)
        if output_file is None:
            base_name = input_file.replace('.csv', '')
            output_file = f"{base_name}_parsed_messages.json"
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
            }
        }

    def display_parsing_summary(self, results: Dict):
        """Display comprehensive parsing summary for OTP, EMI, challan, and transportation"""
        metadata = results['metadata']
        otp_stats = results.get('summary_statistics', {}).get('otp_stats', {})
        emi_stats = results.get('summary_statistics', {}).get('emi_stats', {})
        challan_stats = results.get('summary_statistics', {}).get('challan_stats', {})
        transportation_stats = results.get('summary_statistics', {}).get('transportation_stats', {})
        print("" + "="*90)
        print("ENHANCED MESSAGE PARSING RESULTS SUMMARY v9.3 (DEBUGGED TRANSPORTATION)")
        print("="*90)
        print(f"Total Input Messages: {metadata['total_input_messages']:,}")
        print(f"Total Parsed Messages: {metadata['total_parsed_messages']:,}")
        print(f"  - OTP Messages Found: {metadata['otp_messages_found']:,}")
        print(f"  - EMI Messages Found: {metadata['emi_messages_found']:,}")
        print(f"  - Challan Messages Found: {metadata['challan_messages_found']:,}")
        print(f"  - Transportation Messages Found: {metadata['transportation_messages_found']:,}")
        print(f"Messages Rejected: {metadata['rejected_messages']:,}")
        print(f"Overall Detection Rate: {metadata['detection_rate']}%")
        # OTP Summary
        if otp_stats and otp_stats.get('total_count', 0) > 0:
            print("" + "="*60)
            print("OTP MESSAGES SUMMARY")
            print("="*60)
            distributions = otp_stats.get('distributions', {})
            quality_metrics = otp_stats.get('quality_metrics', {})
            print("Top Companies/Services:")
            for company, count in list(distributions.get('top_companies', {}).items())[:5]:
                percentage = (count / otp_stats['total_count']) * 100
                print(f"  {company}: {count:,} ({percentage:.1f}%)")
            print(f"OTP Quality Metrics:")
            print(f"  Average Confidence Score: {quality_metrics.get('average_confidence_score', 0)}")
            print(f"  High Confidence (>=80): {quality_metrics.get('high_confidence_messages', 0)}")
        # EMI Summary
        if emi_stats and emi_stats.get('total_count', 0) > 0:
            print("" + "="*60)
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
                print(f"EMI Amount Statistics:")
                print(f"  Average EMI: Rs.{amount_stats.get('average_amount', 0):,.2f}")
                print(f"  Total EMI Value: Rs.{amount_stats.get('total_emi_value', 0):,.2f}")
            print(f"EMI Data Completeness:")
            print(f"  Messages with Amount: {quality_metrics.get('messages_with_amount', 0)}/{emi_stats['total_count']}")
            print(f"  Messages with Bank: {quality_metrics.get('messages_with_bank', 0)}/{emi_stats['total_count']}")
        # Challan Summary - Enhanced
        if challan_stats and challan_stats.get('total_count', 0) > 0:
            print("" + "="*60)
            print("TRAFFIC CHALLAN MESSAGES SUMMARY (ENHANCED)")
            print("="*60)
            distributions = challan_stats.get('distributions', {})
            quality_metrics = challan_stats.get('quality_metrics', {})
            fine_stats = challan_stats.get('fine_statistics', {})
            print("Traffic Authorities:")
            for authority, count in distributions.get('authorities', {}).items():
                percentage = (count / challan_stats['total_count']) * 100
                print(f"  {authority}: {count:,} ({percentage:.1f}%)")
            print("Challan Status Distribution:")
            for status, count in distributions.get('status_types', {}).items():
                percentage = (count / challan_stats['total_count']) * 100
                status_emoji = "Paid" if status == 'paid' else "Pending" if status == 'pending' else "Issued"
                print(f"  {status_emoji}: {count:,} ({percentage:.1f}%)")
            if fine_stats:
                print(f"  Fine Amount Statistics:")
                print(f"  Average Fine: Rs.{fine_stats.get('average_fine', 0):,.2f}")
                print(f"  Highest Fine: Rs.{fine_stats.get('max_fine', 0):,.2f}")
                print(f"  Total Fines: Rs.{fine_stats.get('total_fine_value', 0):,.2f}")
            print(f"Challan Data Completeness:")
            print(f"  Messages with Challan Number: {quality_metrics.get('messages_with_challan_number', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Vehicle Number: {quality_metrics.get('messages_with_vehicle_number', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Fine Amount: {quality_metrics.get('messages_with_fine_amount', 0)}/{challan_stats['total_count']}")
            print(f"  Messages with Payment Link: {quality_metrics.get('messages_with_payment_link', 0)}/{challan_stats['total_count']}")
        # Transportation Summary
        if transportation_stats and transportation_stats.get('total_count', 0) > 0:
            print("" + "="*60)
            print("TRANSPORTATION MESSAGES SUMMARY (DEBUGGED)")
            print("="*60)
            distributions = transportation_stats.get('distributions', {})
            quality_metrics = transportation_stats.get('quality_metrics', {})
            print("Transportation Types:")
            for transport_type, count in distributions.get('transport_types', {}).items():
                percentage = (count / transportation_stats['total_count']) * 100
                print(f"  {transport_type.title()}: {count:,} ({percentage:.1f}%)")
            print("Top Service Providers:")
            for provider, count in list(distributions.get('top_providers', {}).items())[:5]:
                percentage = (count / transportation_stats['total_count']) * 100
                print(f"  {provider}: {count:,} ({percentage:.1f}%)")
            print("Top Boarding Places:")
            for place, count in list(distributions.get('top_boarding_places', {}).items())[:5]:
                percentage = (count / transportation_stats['total_count']) * 100
                print(f"  {place}: {count:,} ({percentage:.1f}%)")
            print(f"  Transportation Data Completeness:")
            print(f"  Messages with PNR: {quality_metrics.get('messages_with_pnr', 0)}/{transportation_stats['total_count']}")
            print(f"  Messages with Date of Journey: {quality_metrics.get('messages_with_doj', 0)}/{transportation_stats['total_count']}")
            print(f"  Messages with Boarding Place: {quality_metrics.get('messages_with_boarding_place', 0)}/{transportation_stats['total_count']}")
            print(f"  Messages with Drop Place: {quality_metrics.get('messages_with_drop_place', 0)}/{transportation_stats['total_count']}")
            print(f"  Messages with Provider: {quality_metrics.get('messages_with_provider', 0)}/{transportation_stats['total_count']}")
            print(f"  Messages with Departure Time: {quality_metrics.get('messages_with_departure_time', 0)}/{transportation_stats['total_count']}")

    def interactive_message_analyzer(self):
        """Interactive analyzer for OTP, EMI, challan, and transportation messages"""
        print("Interactive Message Analyzer v9.3 (OTP, EMI, Traffic Challan & Debugged Transportation)")
        print("=" * 70)
        print("Enhanced with transportation parsing for trains, flights, and buses")
        print("Enter messages to analyze (type 'quit' to exit)")
        while True:
            print("" + "-" * 70)
            message = input("Enter message: ").strip()
            if message.lower() in ['quit', 'exit', 'q']:
                break
            if not message:
                continue
            sender = input("Enter sender name (optional): ").strip()
            message_type = input("Message type (otp/emi/challan/transportation/auto) [auto]: ").strip().lower()
            if not message_type:
                message_type = "auto"
            print("Detailed Analysis:")
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
                elif result['message_type'] == 'transportation':
                    print(f"Transport Type: {result.get('transport_type')}")
                    print(f"PNR Number: {result.get('pnr_number')}")
                    print(f"Date of Journey: {result.get('date_of_journey')}")
                    print(f"Boarding Place: {result.get('boarding_place')}")
                    print(f"Drop Place: {result.get('drop_place')}")
                    print(f"Seat Info: {result.get('seat_number')}")
                    print(f"Class: {result.get('class')}")
                    print(f"Platform: {result.get('platform_number')}")
                    print(f"Gate: {result.get('gate_number')}")
                    print(f"Departure Time: {result.get('departure_time')}") # NEW
                    print(f"Service Provider: {result.get('transport_provider')}")
            else:
                print(f"Rejection Reason: {result.get('reason')}")