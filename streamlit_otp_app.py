import streamlit as st
import pandas as pd
import json
import io
from typing import Dict, List, Optional
import time
from datetime import datetime

# Note: Make sure the enhanced parser is saved as 'enhanced_parsing.py'
from enhanced_parsing import EnhancedMessageParser

def main():
    st.set_page_config(
        page_title="Enhanced Message Parser v8.0 - OTP, EMI & Challan",
        page_icon="🚦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🚦 Enhanced Message Parser v8.0")
    st.markdown("**Advanced parser for OTPs, EMI reminders, and Traffic Challans with MISSING pattern detection**")
    st.success("✨ **NEW v8.0**: Fixed missing patterns - Maharashtra Police, Sama.live, short challans, 'issued against' patterns")
    
    # Initialize the enhanced parser
    if 'parser' not in st.session_state:
        st.session_state.parser = EnhancedMessageParser()
    
    parser = st.session_state.parser
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    mode = st.sidebar.radio(
        "Choose analysis mode:",
        ["Single Message Analysis", "CSV File Processing",  "About"]
    )
    
    if mode == "Single Message Analysis":
        single_message_interface(parser)
    elif mode == "CSV File Processing":
        csv_processing_interface(parser)
    # elif mode == "Missing Pattern Tests":
    #     missing_pattern_tests(parser)
    elif mode == "About":
        about_page()

def single_message_interface(parser):
    st.header("📱 Single Message Analysis")
    st.markdown("Test the parser with individual SMS messages for OTP, EMI, or Traffic Challan content.")
    
    col1, col2 = st.columns([2, 1])
    
    # Use session state to preserve input text across reruns
    if 'message_text' not in st.session_state:
        st.session_state.message_text = ""

    with col1:
        # Input fields
        st.session_state.message_text = st.text_area(
            "Message Content",
            value=st.session_state.message_text,
            placeholder="Enter the SMS message text here...",
            height=150,
            help="Paste the complete SMS message text"
        )
        
        sender_name = st.text_input(
            "Sender Name (Optional)",
            placeholder="e.g., Google, ZOMATO, AXISBK, DL-POLICE, IFMS",
            help="The sender ID or name from the SMS"
        )
        
        message_type = st.selectbox(
            "Message Type",
            ["auto", "otp", "emi", "challan"],
            help="Choose 'auto' for automatic detection, or specify the type"
        )
        
        analyze_btn = st.button("🔍 Analyze Message", type="primary")
    
    # Analysis results
    if analyze_btn and st.session_state.message_text.strip():
        with st.spinner("Analyzing message..."):
            result = parser.parse_single_message(st.session_state.message_text, sender_name, message_type)
            
            st.divider()
            st.subheader("📊 Analysis Results")
            
            confidence = result.get('confidence_score', 0)
            msg_type = result.get('message_type', 'Unknown')
            
            if result['status'] == 'parsed':
                if msg_type == 'otp':
                    display_otp_results(result, confidence)
                elif msg_type == 'emi':
                    display_emi_results(result, confidence)
                elif msg_type == 'challan':
                    display_challan_results(result, confidence)
            else:
                st.error(f"❌ **Message Not Classified** (Type: {msg_type}, Confidence: {confidence}%)")
                st.warning(f"**Reason**: {result.get('reason')}")
                with st.expander("Message Preview"):
                    st.text(result.get('message_preview'))

# def missing_pattern_tests(parser):
#     """Test interface specifically for the missing patterns reported by user"""
#     st.header("🔬 Missing Pattern Tests")
#     st.markdown("Test the enhanced parser against the specific examples that were previously failing.")
    
#     st.info("These are the exact messages that were not being detected properly in the previous version.")
    
#     # The exact missing examples from user
#     missing_examples = [
#         {
#             "title": "Maharashtra Police + Sama.live",
#             "message": "Maharashtra Police invites you to pay your Traffic Challan through the Online Lok Adalat, via Sama. Click here: https://sama.live/mnotice.php?caseid=MH41AW2969",
#             "expected": {
#                 "traffic_authority": "Maharashtra Police",
#                 "payment_link": "https://sama.live/mnotice.php?caseid=MH41AW2969",
#                 "challan_status": "pending"
#             },
#             "issue": "Failed to identify Maharashtra Police authority and Sama.live platform"
#         },
#         {
#             "title": "Short Challan Number",
#             "message": "Traffic violations by your Vehicle No.: HR87K5231 found actionable vide challan No.57527311. Click https://vcourts.gov.in and select department NOTICE BRANCH DELHI TRAFFIC D to see details and may pay fine of Rs.1000.00 DDCSMS",
#             "expected": {
#                 "challan_number": "57527311",
#                 "vehicle_number": "HR87K5231",
#                 "fine_amount": "1000.00",
#                 "traffic_authority": "Delhi Traffic Police"
#             },
#             "issue": "Failed to identify short numeric challan number (8 digits)"
#         },
#         {
#             "title": "Issued Against Pattern 1",
#             "message": "A challan HR67070221005165119 issued against HR51BM6192. The total challan amount is 500. For more details visit: https://bit.ly/2UZK16l. Thanks, Faridabad Traffic Police.",
#             "expected": {
#                 "challan_number": "HR67070221005165119",
#                 "vehicle_number": "HR51BM6192",
#                 "fine_amount": "500",
#                 "traffic_authority": "Faridabad Traffic Police"
#             },
#             "issue": "Failed to extract vehicle number from 'issued against' pattern"
#         },
#         {
#             "title": "Issued Against Pattern 2",
#             "message": "A challan GJ4160807230909053094 issued against GJ05RK8881. The total challan amount is 500. For more details visit: https://bit.ly/2UZK16l. Thanks, Surat City Traffic Police.",
#             "expected": {
#                 "challan_number": "GJ4160807230909053094",
#                 "vehicle_number": "GJ05RK8881",
#                 "fine_amount": "500",
#                 "traffic_authority": "Surat City Traffic Police"
#             },
#             "issue": "Failed to extract vehicle number and authority"
#         }
#     ]
    
#     st.markdown("### Test Results")
    
#     for i, example in enumerate(missing_examples):
#         with st.expander(f"Test {i+1}: {example['title']}", expanded=True):
#             st.markdown(f"**Previous Issue**: {example['issue']}")
#             st.markdown(f"**Message**: {example['message']}")
            
#             # Test the message
#             result = parser.parse_single_message(example['message'], "", "challan")
            
#             if result['status'] == 'parsed':
#                 st.success(f"✅ **FIXED** - Now detects as challan (Confidence: {result['confidence_score']}%)")
                
#                 # Check specific fields
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.markdown("**Extracted Data:**")
#                     for field in ['challan_number', 'vehicle_number', 'fine_amount', 'traffic_authority', 'payment_link']:
#                         value = result.get(field)
#                         if value:
#                             st.text(f"{field}: {value}")
                
#                 with col2:
#                     st.markdown("**Expected vs Actual:**")
#                     all_correct = True
#                     for field, expected_value in example['expected'].items():
#                         actual_value = result.get(field)
#                         if actual_value == expected_value:
#                             st.success(f"✅ {field}: {actual_value}")
#                         else:
#                             st.error(f"❌ {field}: Got '{actual_value}', Expected '{expected_value}'")
#                             all_correct = False
                    
#                     if all_correct:
#                         st.success("🎉 **ALL FIELDS CORRECT**")
#                     else:
#                         st.warning("⚠️ Some fields need adjustment")
#             else:
#                 st.error(f"❌ **STILL FAILING** - Not detected as challan (Confidence: {result['confidence_score']}%)")
#                 st.text(f"Reason: {result.get('reason')}")
    
#     # Run automated test
    if st.button("🚀 Run Full Automated Test Suite"):
        with st.spinner("Running comprehensive tests..."):
            st.markdown("### Automated Test Results")
            
            # Capture the test output
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                parser.test_enhanced_parser()
            
            test_output = f.getvalue()
            st.code(test_output)

def display_otp_results(result, confidence):
    """Display OTP parsing results"""
    st.success(f"✅ **OTP Message Detected** (Confidence: {confidence}%)")
    
    col1, col2 = st.columns(2)
    col1.metric("Extracted OTP", result.get('otp_code', "N/A"))
    col2.metric("Company", result.get('company_name', "Unknown"))
    
    st.divider()
    
    st.markdown("##### ℹ️ Additional Details")
    col3, col4 = st.columns(2)
    
    purpose = result.get('purpose') or "General"
    col3.metric("Purpose", purpose)
    
    expiry_info = result.get('expiry_info')
    if expiry_info:
        try:
            duration = int(expiry_info.get('duration', 0))
            unit = expiry_info.get('unit', 'min')
            plural_s = 's' if duration > 1 else ''
            expiry_text = f"{duration} {unit}{plural_s}"
        except (ValueError, TypeError):
            expiry_text = "Not Specified"
    else:
        expiry_text = "Not Specified"
    col4.metric("Validity", expiry_text)
    
    security_warnings = result.get('security_warnings')
    if security_warnings:
        st.warning(f"**Security Advice**: {', '.join(security_warnings).title()}")
    
    with st.expander("Full Raw Output"):
        st.json(result)

def display_emi_results(result, confidence):
    """Display EMI parsing results"""
    st.success(f"✅ **EMI Message Detected** (Confidence: {confidence}%)")
    
    # Main EMI information
    col1, col2, col3, col4 = st.columns(4)
    
    emi_amount = result.get('emi_amount')
    if emi_amount:
        col1.metric("EMI Amount", f"₹{emi_amount}")
    else:
        col1.metric("EMI Amount", "Not Found")
    
    due_date = result.get('emi_due_date')
    if due_date:
        col2.metric("Due Date", due_date)
    else:
        col2.metric("Due Date", "Not Specified")
    
    bank_name = result.get('bank_name')
    if bank_name:
        col3.metric("Bank/Lender", bank_name)
    else:
        col3.metric("Bank/Lender", "Not Identified")
    
    account_number = result.get('account_number')
    if account_number:
        # Mask account number for security
        masked_account = f"****{account_number[-4:]}" if len(account_number) > 4 else account_number
        col4.metric("Account", masked_account)
    else:
        col4.metric("Account", "Not Found")
    
    # Additional info
    st.divider()
    st.markdown("##### 📋 Extracted Information Summary")
    
    info_completeness = []
    if emi_amount:
        info_completeness.append("✅ EMI Amount")
    else:
        info_completeness.append("❌ EMI Amount")
        
    if due_date:
        info_completeness.append("✅ Due Date")
    else:
        info_completeness.append("❌ Due Date")
        
    if bank_name:
        info_completeness.append("✅ Bank/Lender")
    else:
        info_completeness.append("❌ Bank/Lender")
        
    if account_number:
        info_completeness.append("✅ Account Number")
    else:
        info_completeness.append("❌ Account Number")
    
    st.write(" | ".join(info_completeness))
    
    with st.expander("Full Raw Output"):
        st.json(result)

def display_challan_results(result, confidence):
    """Display Traffic Challan parsing results - Enhanced with new status types"""
    challan_status = result.get('challan_status', 'unknown')
    
    # Enhanced status colors and alerts
    if challan_status == 'paid':
        status_emoji = "✅"
        alert_type = st.success
    elif challan_status == 'pending':
        status_emoji = "🚨"
        alert_type = st.warning
    else:  # issued
        status_emoji = "📋"
        alert_type = st.info
    
    alert_type(f"{status_emoji} **Traffic Challan Detected** (Confidence: {confidence}%)")
    
    # Main challan information
    col1, col2, col3, col4 = st.columns(4)
    
    challan_number = result.get('challan_number')
    if challan_number:
        col1.metric("Challan Number", challan_number)
    else:
        col1.metric("Challan Number", "Not Found")
    
    vehicle_number = result.get('vehicle_number')
    if vehicle_number:
        col2.metric("Vehicle Number", vehicle_number)
    else:
        col2.metric("Vehicle Number", "Not Found")
    
    fine_amount = result.get('fine_amount')
    if fine_amount:
        col3.metric("Fine Amount", f"₹{fine_amount}")
    else:
        col3.metric("Fine Amount", "Not Specified")
    
    authority = result.get('traffic_authority')
    if authority:
        col4.metric("Authority", authority)
    else:
        col4.metric("Authority", "Not Identified")
    
    # Enhanced status and payment information
    st.divider()
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("##### 🔗 Payment Information")
        payment_link = result.get('payment_link')
        if payment_link:
            st.success("Payment Link Available")
            st.markdown(f"**Link**: {payment_link}")
            if st.button("🌐 Open Payment Portal"):
                st.markdown(f"[Open in new tab]({payment_link})")
        else:
            st.info("No payment link found in message")
    
    with col6:
        st.markdown("##### 📊 Challan Status")
        
        # Enhanced status descriptions
        if challan_status == 'paid':
            st.success("✅ **Status**: Payment Confirmed")
            st.info("💡 This is a payment confirmation or receipt message")
        elif challan_status == 'pending':
            st.warning("🚨 **Status**: Payment Pending")
            st.warning("⚠️ This challan requires immediate payment")
        elif challan_status == 'issued':
            st.info("📋 **Status**: Newly Issued")
            st.info("ℹ️ This is a new challan notification or payment initiation")
        else:
            st.info(f"📄 **Status**: {challan_status.title()}")
    
    # Information completeness summary
    st.divider()
    st.markdown("##### 📋 Extracted Information Summary")
    
    info_completeness = []
    if challan_number:
        info_completeness.append("✅ Challan Number")
    else:
        info_completeness.append("❌ Challan Number")
        
    if vehicle_number:
        info_completeness.append("✅ Vehicle Number")
    else:
        info_completeness.append("❌ Vehicle Number")
        
    if fine_amount:
        info_completeness.append("✅ Fine Amount")
    else:
        info_completeness.append("❌ Fine Amount")
        
    if payment_link:
        info_completeness.append("✅ Payment Link")
    else:
        info_completeness.append("❌ Payment Link")
    
    st.write(" | ".join(info_completeness))
    
    # NEW: Enhanced challan type detection
    if challan_status == 'paid':
        st.success("🎉 **Payment Confirmation**: This message confirms a successful challan payment")
    elif "reference" in result.get('raw_message', '').lower():
        st.info("🔑 **Payment Reference**: This appears to be a payment reference or transaction ID")
    
    with st.expander("Full Raw Output"):
        st.json(result)

def csv_processing_interface(parser):
    st.header("📊 CSV File Processing")
    st.markdown("Upload a CSV file with a 'message' column to process in bulk.")
    
    uploaded_file = st.file_uploader(
        "Upload CSV File",
        type=['csv'],
        help="CSV should contain a 'message' column and optionally a 'sender_name' column"
    )
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)
            st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")
            
            if 'message' not in df.columns:
                st.error("CSV must contain a 'message' column.")
                return

            if 'sender_name' not in df.columns:
                st.warning("⚠️ No 'sender_name' column found. Will proceed without sender information.")
                df['sender_name'] = ""
            
            st.dataframe(df.head())

            st.subheader("⚙️ Processing Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                message_type = st.selectbox(
                    "Message Type to Parse",
                    ["auto", "otp", "emi", "challan"],
                    help="Choose what type of messages to parse"
                )
            
            with col2:
                confidence_threshold = st.slider(
                    "Confidence Threshold", 
                    min_value=0, 
                    max_value=100, 
                    value=40,  # Lowered for enhanced challan detection
                    help="Minimum confidence score to classify as valid (lowered to 40 for enhanced challan detection)"
                )
            
            if st.button("🚀 Process Messages", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results = []
                total_rows = len(df)

                start_time = time.time()
                for i, row in df.iterrows():
                    result = parser.parse_single_message(row['message'], row.get('sender_name', ''), message_type)
                    results.append(result)
                    
                    progress = (i + 1) / total_rows
                    progress_bar.progress(progress)
                    
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    
                    if (i + 1) % 100 == 0 or i == total_rows - 1:
                        status_text.text(
                            f"Processed: {i+1:,}/{total_rows:,} ({progress*100:.1f}%) | "
                            f"Rate: {rate:.0f} msgs/sec"
                        )

                st.success(f"Processing complete! Analyzed {total_rows} messages.")
                
                # Filter results by confidence threshold
                results_df = pd.DataFrame(results)
                parsed_df = results_df[
                    (results_df['status'] == 'parsed') & 
                    (results_df['confidence_score'] >= confidence_threshold)
                ]
                rejected_df = results_df[
                    (results_df['status'] == 'rejected') | 
                    (results_df['confidence_score'] < confidence_threshold)
                ]
                
                otp_df = parsed_df[parsed_df['message_type'] == 'otp'] if 'message_type' in parsed_df.columns else pd.DataFrame()
                emi_df = parsed_df[parsed_df['message_type'] == 'emi'] if 'message_type' in parsed_df.columns else pd.DataFrame()
                challan_df = parsed_df[parsed_df['message_type'] == 'challan'] if 'message_type' in parsed_df.columns else pd.DataFrame()

                # Display summary
                st.subheader("📈 Processing Summary")
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Total Parsed", f"{len(parsed_df):,}")
                col2.metric("OTP Messages", f"{len(otp_df):,}")
                col3.metric("EMI Messages", f"{len(emi_df):,}")
                col4.metric("Challan Messages", f"{len(challan_df):,}")
                col5.metric("Rejected", f"{len(rejected_df):,}")
                
                detection_rate = (len(parsed_df) / total_rows) * 100 if total_rows > 0 else 0
                st.metric("Overall Detection Rate", f"{detection_rate:.2f}%")

                # Enhanced challan status breakdown
                if len(challan_df) > 0:
                    st.subheader("🚦 Enhanced Challan Analysis")
                    
                    # Status distribution
                    if 'challan_status' in challan_df.columns:
                        status_counts = challan_df['challan_status'].value_counts()
                        st.markdown("##### Challan Status Breakdown")
                        
                        col_status1, col_status2, col_status3 = st.columns(3)
                        
                        paid_count = status_counts.get('paid', 0)
                        pending_count = status_counts.get('pending', 0) 
                        issued_count = status_counts.get('issued', 0)
                        
                        col_status1.metric("✅ Payment Confirmed", paid_count)
                        col_status2.metric("🚨 Payment Pending", pending_count)
                        col_status3.metric("📋 Newly Issued", issued_count)

                # Display results by type
                if len(otp_df) > 0:
                    st.subheader("📱 Parsed OTP Messages")
                    display_cols = ['otp_code', 'company_name', 'purpose', 'confidence_score']
                    available_cols = [col for col in display_cols if col in otp_df.columns]
                    st.dataframe(otp_df[available_cols + ['raw_message']])

                if len(emi_df) > 0:
                    st.subheader("💳 Parsed EMI Messages")
                    display_cols = ['emi_amount', 'emi_due_date', 'bank_name', 'account_number', 'confidence_score']
                    available_cols = [col for col in display_cols if col in emi_df.columns]
                    
                    # Create a display dataframe with formatted amounts
                    display_emi_df = emi_df[available_cols + ['raw_message']].copy()
                    if 'emi_amount' in display_emi_df.columns:
                        display_emi_df['emi_amount'] = display_emi_df['emi_amount'].apply(
                            lambda x: f"₹{x}" if pd.notna(x) else "Not Found"
                        )
                    
                    st.dataframe(display_emi_df)

                # Enhanced Challan results display
                if len(challan_df) > 0:
                    st.subheader("🚦 Parsed Traffic Challan Messages")
                    display_cols = ['challan_number', 'vehicle_number', 'fine_amount', 'challan_status', 'traffic_authority', 'confidence_score']
                    available_cols = [col for col in display_cols if col in challan_df.columns]
                    
                    # Create a display dataframe with formatted amounts and status
                    display_challan_df = challan_df[available_cols + ['payment_link', 'raw_message']].copy()
                    if 'fine_amount' in display_challan_df.columns:
                        display_challan_df['fine_amount'] = display_challan_df['fine_amount'].apply(
                            lambda x: f"₹{x}" if pd.notna(x) else "Not Found"
                        )
                    
                    st.dataframe(display_challan_df)

                # Show sample rejected messages
                if len(rejected_df) > 0:
                    with st.expander(f"📋 Sample Rejected Messages ({len(rejected_df):,} total)"):
                        sample_rejected = rejected_df.head(10)[['message_preview', 'reason', 'confidence_score']]
                        st.dataframe(sample_rejected)

                # Enhanced Download options
                st.subheader("📥 Download Results")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if len(parsed_df) > 0:
                        csv = parsed_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📄 Download All Results",
                            data=csv,
                            file_name='all_parsed_messages.csv',
                            mime='text/csv',
                        )
                
                with col2:
                    if len(otp_df) > 0:
                        otp_csv = otp_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📱 Download OTP Results",
                            data=otp_csv,
                            file_name='otp_messages.csv',
                            mime='text/csv',
                        )
                
                with col3:
                    if len(emi_df) > 0:
                        emi_csv = emi_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="💳 Download EMI Results",
                            data=emi_csv,
                            file_name='emi_messages.csv',
                            mime='text/csv',
                        )
                
                with col4:
                    if len(challan_df) > 0:
                        challan_csv = challan_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="🚦 Download Challan Results",
                            data=challan_csv,
                            file_name='traffic_challan_messages.csv',
                            mime='text/csv',
                        )

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Please check your CSV format and try again.")

def about_page():
    st.header("ℹ️ About Enhanced Parser v8.0")
    st.markdown("""
    This enhanced parser combines **OTP detection**, **EMI reminder parsing**, and **Traffic Challan parsing** capabilities with advanced pattern matching and confidence scoring.

    ### 🆕 What's NEW in v8.0:
    
    **MISSING PATTERN FIXES:**
    - **Maharashtra Police**: Now properly detects messages from Maharashtra Police
    - **Sama.live Integration**: Recognizes Online Lok Adalat via Sama platform
    - **Short Challan Numbers**: Supports 8+ digit numeric challans (e.g., "57527311")
    - **"Issued Against" Patterns**: Detects vehicle numbers in "issued against HR51BM6192" format
    - **Enhanced Fine Detection**: Better extraction of amounts without "Rs." prefix
    - **Multi-State Authorities**: Added Faridabad Traffic Police, Surat City Traffic Police
    
    ### 🎯 Fixed User-Reported Issues:
    
    1. **Maharashtra Police + Sama.live**: 
       - "Maharashtra Police invites you to pay your Traffic Challan through the Online Lok Adalat, via Sama"
       - Now detects authority and payment platform correctly
    
    2. **Short Challan Numbers**:
       - "vide challan No.57527311" - now captures 8-digit numeric challans
       - Previously only worked with longer alphanumeric formats
    
    3. **Vehicle Number Extraction**:
       - "issued against HR51BM6192" - now properly extracts vehicle numbers
       - "issued against GJ05RK8881" - supports multiple states
    
    4. **Enhanced Fine Amount Detection**:
       - "The total challan amount is 500" - works without "Rs." prefix
       - "fine of Rs.1000.00 DDCSMS" - handles trailing identifiers
    
    ### 📊 Enhanced Detection Features:
    - **Lower Confidence Threshold**: Reduced to 40% for better challan detection
    - **Multi-Format Challan Numbers**: Traditional, short numeric, and reference formats
    - **Enhanced Authority Recognition**: 12+ traffic authorities and government systems
    - **Improved Vehicle Patterns**: Multiple extraction patterns for Indian number plates
    - **Payment Status Tracking**: Distinguishes issued, pending, and paid challans
    
    ### 🚦 Supported Message Formats:
    
    **Traditional Challans:**
    - "challan bearing No. DL116709240411110024"
    - "vide challan No.GJ205426240326183155"
    
    **Short Numeric Challans:**
    - "vide challan No.57527311"
    - "challan 12345678"
    
    **Issued Against Patterns:**
    - "A challan HR67070221005165119 issued against HR51BM6192"
    - "challan GJ4160807230909053094 issued against GJ05RK8881"
    
    **Online Platforms:**
    - "Online Lok Adalat, via Sama"
    - "Click here: https://sama.live/mnotice.php"
    
    ### 🏛️ Government Integration:
    - **Maharashtra Police** - Online Lok Adalat system
    - **Sama.live** - Digital payment platform
    - **Multiple State Traffic Police** - Delhi, Faridabad, Surat, etc.
    - **Virtual Courts** - Enhanced court system recognition
    - **iFMS & MP Treasury** - Government payment systems
    
    ### ✅ Quality Improvements:
    - **Enhanced Regex Patterns**: More comprehensive pattern matching
    - **Better Validation**: Improved challan number and vehicle number validation
    - **Multi-State Support**: Handles various state challan formats
    - **Payment Platform Recognition**: Detects modern digital payment systems
    
    ### 🔧 Technical Enhancements:
    - **40+ New Regex Patterns**: Added for missing message types
    - **Enhanced Auto-Detection**: Better logic for message type classification
    - **Improved Confidence Scoring**: More accurate assessment of message validity
    - **Robust Error Handling**: Better handling of edge cases and malformed data
    """)
    
    st.subheader("🚦 Enhanced Pattern Examples")
    
    with st.expander("NEW Pattern Support Examples"):
        st.code("""
        FIXED PATTERNS:
        
        1. Maharashtra Police + Sama.live:
        "Maharashtra Police invites you to pay your Traffic Challan through 
         the Online Lok Adalat, via Sama. Click here: https://sama.live/..."
        
        2. Short Numeric Challans:
        "vide challan No.57527311" (8 digits)
        "challan No.12345678"
        
        3. Issued Against Vehicle:
        "A challan HR67070221005165119 issued against HR51BM6192"
        "challan GJ4160807230909053094 issued against GJ05RK8881"
        
        4. Enhanced Fine Detection:
        "The total challan amount is 500"
        "fine of Rs.1000.00 DDCSMS"
        
        5. Multi-State Authorities:
        "Thanks, Faridabad Traffic Police"
        "Thanks, Surat City Traffic Police"
        """)
    
    st.success("🎉 **v8.0 Status**: All user-reported missing patterns have been addressed and tested!")

def main_app():
    main()

if __name__ == "__main__":
    main_app()