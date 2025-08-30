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
        page_title="Enhanced Message Parser - OTP & EMI",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎯 Enhanced Message Parser")
    st.markdown("**Advanced parser for OTPs and EMI reminders with high accuracy**")
    
    # Initialize the enhanced parser
    if 'parser' not in st.session_state:
        st.session_state.parser = EnhancedMessageParser()
    
    parser = st.session_state.parser
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    mode = st.sidebar.radio(
        "Choose analysis mode:",
        ["Single Message Analysis", "CSV File Processing", "About"]
    )
    
    if mode == "Single Message Analysis":
        single_message_interface(parser)
    elif mode == "CSV File Processing":
        csv_processing_interface(parser)
    elif mode == "About":
        about_page()

def single_message_interface(parser):
    st.header("📱 Single Message Analysis")
    st.markdown("Test the parser with individual SMS messages for OTP or EMI content.")
    
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
            placeholder="e.g., Google, ZOMATO, AXISBK, IDFC",
            help="The sender ID or name from the SMS"
        )
        
        message_type = st.selectbox(
            "Message Type",
            ["auto", "otp", "emi"],
            help="Choose 'auto' for automatic detection, or specify the type"
        )
        
        analyze_btn = st.button("🔍 Analyze Message", type="primary")
    
    with col2:
        st.markdown("### Quick Test Examples")
        
        # OTP Examples
        st.markdown("**OTP Examples**")
        otp_examples = {
            "Instagram": "123 456 is your Instagram login code. Don't share it.",
            "Signal": "Your Signal registration code is 246-810.",
            "Axis Bank": "Your Axis Bank OTP is 224466. Valid for 5 minutes.",
            "Google": "G-123456 is your Google verification code.",
        }
        for label, example in otp_examples.items():
            if st.button(f"Load: {label}", key=f"otp_{label}"):
                st.session_state.message_text = example
                st.rerun()
        
        # EMI Examples
        st.markdown("**EMI Examples**")
        emi_examples = {
            "IDFC Bank": "Your IDFC FIRST Bank loan EMI of Rs 2446, a/c: 65689256, is PENDING!",
            "Bike Bazaar": "EMI payment of Rs. 3406.00/- for Jul'2024 for loan account RTMN2W000005200062 not paid.",
            "Chola Finance": "EMI payment Rs 27267 for the month has bounced. Pay now to avoid penalty.",
        }
        for label, example in emi_examples.items():
            if st.button(f"Load: {label}", key=f"emi_{label}"):
                st.session_state.message_text = example
                st.rerun()

        st.markdown("**False Positives**")
        false_examples = {
            "Order Number": "Thank you for your order #567890 from Zomato.",
            "EMI Promo": "Get easy EMI options starting from Rs 999! 0% interest!",
            "Balance": "Your account balance is INR 12,345.67",
        }
        for label, example in false_examples.items():
            if st.button(f"Load: {label}", key=f"false_{label}"):
                st.session_state.message_text = example
                st.rerun()

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
            else:
                st.error(f"❌ **Message Not Classified** (Type: {msg_type}, Confidence: {confidence}%)")
                st.warning(f"**Reason**: {result.get('reason')}")
                with st.expander("Message Preview"):
                    st.text(result.get('message_preview'))

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
                    ["auto", "otp", "emi"],
                    help="Choose what type of messages to parse"
                )
            
            with col2:
                confidence_threshold = st.slider(
                    "Confidence Threshold", 
                    min_value=0, 
                    max_value=100, 
                    value=50,
                    help="Minimum confidence score to classify as valid (default: 50)"
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
                
                # Separate results by type
                results_df = pd.DataFrame(results)
                parsed_df = results_df[results_df['status'] == 'parsed']
                rejected_df = results_df[results_df['status'] == 'rejected']
                
                otp_df = parsed_df[parsed_df['message_type'] == 'otp'] if 'message_type' in parsed_df.columns else pd.DataFrame()
                emi_df = parsed_df[parsed_df['message_type'] == 'emi'] if 'message_type' in parsed_df.columns else pd.DataFrame()

                # Display summary
                st.subheader("📈 Processing Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Parsed", f"{len(parsed_df):,}")
                col2.metric("OTP Messages", f"{len(otp_df):,}")
                col3.metric("EMI Messages", f"{len(emi_df):,}")
                col4.metric("Rejected", f"{len(rejected_df):,}")
                
                detection_rate = (len(parsed_df) / total_rows) * 100 if total_rows > 0 else 0
                st.metric("Overall Detection Rate", f"{detection_rate:.2f}%")

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
                    
                    # EMI Statistics
                    if 'emi_amount' in emi_df.columns:
                        amounts = []
                        for amount_str in emi_df['emi_amount'].dropna():
                            try:
                                amount = float(str(amount_str).replace(',', ''))
                                amounts.append(amount)
                            except ValueError:
                                continue
                        
                        if amounts:
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Average EMI", f"₹{sum(amounts)/len(amounts):,.2f}")
                            col2.metric("Highest EMI", f"₹{max(amounts):,.2f}")
                            col3.metric("Total EMI Value", f"₹{sum(amounts):,.2f}")

                # Show sample rejected messages
                if len(rejected_df) > 0:
                    with st.expander(f"📋 Sample Rejected Messages ({len(rejected_df):,} total)"):
                        sample_rejected = rejected_df.head(10)[['message_preview', 'reason', 'confidence_score']]
                        st.dataframe(sample_rejected)

                # Download options
                st.subheader("📥 Download Results")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if len(parsed_df) > 0:
                        csv = parsed_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download All Parsed Results",
                            data=csv,
                            file_name='all_parsed_messages.csv',
                            mime='text/csv',
                        )
                
                with col2:
                    if len(otp_df) > 0:
                        otp_csv = otp_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download OTP Results",
                            data=otp_csv,
                            file_name='otp_messages.csv',
                            mime='text/csv',
                        )
                
                with col3:
                    if len(emi_df) > 0:
                        emi_csv = emi_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download EMI Results",
                            data=emi_csv,
                            file_name='emi_messages.csv',
                            mime='text/csv',
                        )

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.error("Please check your CSV format and try again.")

def about_page():
    st.header("ℹ️ About This Enhanced Parser")
    st.markdown("""
    This enhanced parser combines **OTP detection** and **EMI reminder parsing** capabilities using advanced pattern matching and confidence scoring.

    ### 🔍 How It Works:
    
    #### OTP Detection:
    1. **Strong Exclusion First**: Immediately rejects patterns like "order #", "account balance", or promo codes
    2. **Pattern Matching**: Looks for OTP formats (4-8 digits) near keywords like 'OTP', 'code', 'verification'
    3. **Company Recognition**: Identifies services like Google, Instagram, banks, etc.
    4. **Confidence Scoring**: Combines multiple factors to determine likelihood of being an OTP
    
    #### EMI Parsing:
    1. **Promotional Filter**: Automatically rejects EMI promotional messages (0% interest, easy EMI offers)
    2. **Amount Extraction**: Identifies EMI amounts in various formats (Rs. 1,234.50, Rs 1234, etc.)
    3. **Date Parsing**: Extracts due dates in multiple formats (DD/MM/YYYY, Jul'2024, etc.)
    4. **Bank Recognition**: Identifies 15+ major banks and financial institutions
    5. **Account Detection**: Extracts loan account numbers when available
    
    ### 📊 Key Features:
    - **High Accuracy**: Advanced pattern matching reduces false positives
    - **Flexible Input**: Handles various message formats and styles
    - **Comprehensive Output**: Extracts all relevant information
    - **Batch Processing**: Process thousands of messages efficiently
    - **Export Options**: Download results in CSV format
    
    ### 📋 Extracted EMI Fields:
    - **EMI Amount**: Monthly installment amount
    - **Due Date**: Payment due date or month
    - **Bank Name**: Lending institution
    - **Account Number**: Loan account identifier (when available)
    
    ### 🎯 Confidence Scoring:
    Both OTP and EMI parsers use confidence scores (0-100) to determine accuracy:
    - **50+ points**: Message is classified as valid
    - **80+ points**: High confidence classification
    - **Below 50**: Message is rejected
    
    ### 🚫 What Gets Rejected:
    - **OTP**: Order confirmations, promo codes, balance messages, general notifications
    - **EMI**: Promotional offers, loan advertisements, general banking messages
    
    ### 💡 Tips for Best Results:
    1. Include sender information when available
    2. Use complete message text (don't truncate)
    3. For CSV processing, ensure proper encoding (UTF-8)
    4. Review confidence scores - higher scores indicate better accuracy
    """)
    
    st.subheader("🏦 Supported Banks & Lenders")
    banks_col1, banks_col2, banks_col3 = st.columns(3)
    
    with banks_col1:
        st.markdown("""
        **Major Banks:**
        - IDFC FIRST Bank
        - Axis Bank
        - HDFC Bank
        - SBI
        - ICICI Bank
        - Kotak Bank
        """)
    
    with banks_col2:
        st.markdown("""
        **NBFCs:**
        - Bajaj Finance
        - Chola Finance
        - Fullerton India
        - Mahindra Finance
        - Tata Capital
        """)
    
    with banks_col3:
        st.markdown("""
        **Specialized Lenders:**
        - L&T Finance
        - Hero FinCorp
        - TVS Credit
        - Bike Bazaar Finance
        """)
    
    st.subheader("🔧 Technical Details")
    with st.expander("Pattern Matching Examples"):
        st.code("""
        EMI Amount Patterns:
        - "EMI payment of Rs. 3406.00/-"
        - "loan EMI of Rs 2446"
        - "EMI Amount is: 1500"
        
        Due Date Patterns:
        - "for Jul'2024"
        - "due on 15/08/2024"
        - "pay by 20/12/2021"
        
        Account Number Patterns:
        - "loan account RTMN2W000005200062"
        - "Loan a/c: 65689256"
        - "account: ABC123XYZ789"
        """)
    
    st.info("💡 **Note**: This parser is designed for Indian SMS formats and may need adjustments for other regions.")

def main_app():
    main()

if __name__ == "__main__":
    main_app()


































# import streamlit as st
# import pandas as pd
# import json
# import io
# from typing import Dict, List, Optional
# import time
# from datetime import datetime

# # Import the updated and enhanced OTP parser class
# from parsing import EnhancedOTPMessageParser

# def main():
#     st.set_page_config(
#         page_title="High-Precision OTP Parser",
#         page_icon="🎯",
#         layout="wide",
#         initial_sidebar_state="expanded"
#     )
    
#     st.title("🎯 High-Precision OTP Parser")
#     st.markdown("**An advanced parser to accurately identify OTPs and reject false positives.**")
    
#     # Initialize the enhanced parser
#     if 'parser' not in st.session_state:
#         st.session_state.parser = EnhancedOTPMessageParser()
    
#     parser = st.session_state.parser
    
#     # Sidebar navigation
#     st.sidebar.title("Navigation")
#     mode = st.sidebar.radio(
#         "Choose analysis mode:",
#         ["Single Message Analysis", "CSV File Processing", "About"]
#     )
    
#     if mode == "Single Message Analysis":
#         single_message_interface(parser)
#     elif mode == "CSV File Processing":
#         csv_processing_interface(parser)
#     elif mode == "About":
#         about_page()

# def single_message_interface(parser):
#     st.header("📱 Single Message Analysis")
#     st.markdown("Test the parser with individual SMS messages.")
    
#     col1, col2 = st.columns([2, 1])
    
#     # Use session state to preserve input text across reruns
#     if 'message_text' not in st.session_state:
#         st.session_state.message_text = ""

#     with col1:
#         # Input fields
#         st.session_state.message_text = st.text_area(
#             "Message Content",
#             value=st.session_state.message_text,
#             placeholder="Enter the SMS message text here...",
#             height=150,
#             help="Paste the complete SMS message text"
#         )
        
#         sender_name = st.text_input(
#             "Sender Name (Optional)",
#             placeholder="e.g., Google, ZOMATO, AXISBK",
#             help="The sender ID or name from the SMS"
#         )
        
#         analyze_btn = st.button("🔍 Analyze Message", type="primary")
    
#     with col2:
#         st.markdown("### Quick Test Examples")
        
#         st.markdown("**True OTPs (Should be Parsed)**")
#         true_otp_examples = {
#             "Instagram (Space)": "123 456 is your Instagram login code. Don't share it.",
#             "Signal (Hyphen)": "Your Signal registration code is 246-810.",
#             "Axis Bank": "Your Axis Bank One-Time Password is 224466. This is valid for the next 5 minutes.",
#         }
#         for label, example in true_otp_examples.items():
#             if st.button(f"Load: {label}", key=f"true_{label}"):
#                 st.session_state.message_text = example
#                 st.rerun()

#         st.markdown("**False Positives (Should be Rejected)**")
#         false_positive_examples = {
#             "Zomato Order #": "Thank you for your order #567890 from Zomato.",
#             "Promo Code": "Flash Sale! Get 50% off on orders above Rs. 1500. Use code SAVE50.",
#             "Account Balance": "Your account balance is INR 12,345.67 as of 29-Aug-2025.",
#         }
#         for label, example in false_positive_examples.items():
#             if st.button(f"Load: {label}", key=f"false_{label}"):
#                 st.session_state.message_text = example
#                 st.rerun()

#     # Analysis results
#     if analyze_btn and st.session_state.message_text.strip():
#         with st.spinner("Analyzing message..."):
#             result = parser.parse_single_message(st.session_state.message_text, sender_name)
            
#             st.divider()
#             st.subheader("📊 Analysis Results")
            
#             confidence = result.get('confidence_score', 0)
            
#             if result['status'] == 'parsed':
#                 st.success(f"✅ **OTP Message Detected** (Confidence: {confidence}%)")
                
#                 # --- Main Metrics ---
#                 col1, col2 = st.columns(2)
#                 col1.metric("Extracted OTP", result.get('otp_code', "N/A"))
#                 col2.metric("Identified Company", result.get('company_name', "Unknown"))
                
#                 st.divider()
                
#                 # --- Additional Details ---
#                 st.markdown("##### ℹ️ Additional Details")
#                 col3, col4 = st.columns(2)

#                 # Purpose of the OTP
#                 purpose = result.get('purpose') or "General"
#                 col3.metric("Purpose", purpose)

#                 # Expiry Information
#                 expiry_info = result.get('expiry_info')
#                 if expiry_info:
#                     try:
#                         duration = int(expiry_info.get('duration', 0))
#                         unit = expiry_info.get('unit', 'min')
#                         plural_s = 's' if duration > 1 else ''
#                         expiry_text = f"{duration} {unit}{plural_s}"
#                     except (ValueError, TypeError):
#                         expiry_text = "Not Specified"
#                 else:
#                     expiry_text = "Not Specified"
#                 col4.metric("Validity", expiry_text)

#                 # Security Warnings
#                 security_warnings = result.get('security_warnings')
#                 if security_warnings:
#                     st.warning(f"**Security Advice**: {', '.join(security_warnings).title()}")

#                 with st.expander("Full Raw Output"):
#                     st.json(result)
            
#             else:
#                 st.error(f"❌ **Not an OTP Message** (Confidence: {confidence}%)")
#                 st.warning(f"**Reason**: {result.get('reason')}")
#                 with st.expander("Message Preview"):
#                     st.text(result.get('message_preview'))

# def csv_processing_interface(parser):
#     st.header("📊 CSV File Processing")
#     st.markdown("Upload a CSV file with a 'message' column to process in bulk.")
    
#     uploaded_file = st.file_uploader(
#         "Upload CSV File",
#         type=['csv'],
#         help="CSV should contain a 'message' column and optionally a 'sender_name' column"
#     )
    
#     if uploaded_file:
#         try:
#             df = pd.read_csv(uploaded_file, dtype=str)
#             st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")
            
#             if 'message' not in df.columns:
#                 st.error("CSV must contain a 'message' column.")
#                 return

#             if 'sender_name' not in df.columns:
#                 st.warning("⚠️ No 'sender_name' column found. Will proceed without sender information.")
#                 df['sender_name'] = ""
            
#             st.dataframe(df.head())

#             st.subheader("⚙️ Processing Options")
#             confidence_threshold = st.slider(
#                 "Confidence Threshold", 
#                 min_value=0, 
#                 max_value=100, 
#                 value=50,
#                 help="Minimum confidence score to classify as OTP (default: 50)"
#             )
            
#             if st.button("🚀 Process Messages", type="primary"):
#                 progress_bar = st.progress(0)
#                 status_text = st.empty()
#                 results = []
#                 total_rows = len(df)

#                 start_time = time.time()
#                 for i, row in df.iterrows():
#                     result = parser.parse_single_message(row['message'], row.get('sender_name', ''))
#                     results.append(result)
                    
#                     progress = (i + 1) / total_rows
#                     progress_bar.progress(progress)
                    
#                     elapsed = time.time() - start_time
#                     rate = (i + 1) / elapsed if elapsed > 0 else 0
                    
#                     status_text.text(
#                         f"Processed: {i+1:,}/{total_rows:,} ({progress*100:.1f}%) | "
#                         f"Rate: {rate:.0f} msgs/sec"
#                     )

#                 st.success(f"Processing complete! Analyzed {total_rows} messages.")
                
#                 results_df = pd.DataFrame(results)
                
#                 otp_df = results_df[results_df['status'] == 'parsed']
#                 rejected_df = results_df[results_df['status'] == 'rejected']

#                 st.subheader("📈 Processing Summary")
#                 col1, col2, col3 = st.columns(3)
#                 col1.metric("OTP Messages Found", f"{len(otp_df):,}")
#                 col2.metric("Messages Rejected", f"{len(rejected_df):,}")
#                 detection_rate = (len(otp_df) / total_rows) * 100 if total_rows > 0 else 0
#                 col3.metric("Detection Rate", f"{detection_rate:.2f}%")


#                 st.subheader("📋 Parsed OTP Messages")
#                 st.dataframe(otp_df)

#                 csv = results_df.to_csv(index=False).encode('utf-8')
#                 st.download_button(
#                     label="Download Full Results as CSV",
#                     data=csv,
#                     file_name='otp_analysis_results.csv',
#                     mime='text/csv',
#                 )
#         except Exception as e:
#             st.error(f"An error occurred: {e}")

# def about_page():
#     st.header("ℹ️ About This Parser")
#     st.markdown("""
#     This parser uses a **robust, keyword-driven confidence scoring system** to accurately identify OTPs.

#     ### How It Works:
#     1.  **Strong Exclusion First**: The parser immediately checks for high-confidence non-OTP patterns like "order #", "account balance", or alphanumeric promo codes. If found, the message is instantly rejected.
#     2.  **Flexible Extraction**: It then looks for numbers formatted like OTPs (e.g., `123456`, `123-456`, `123 456`) that are located near strong keywords like 'OTP', 'code', or 'password'.
#     3.  **Confidence Scoring**: It calculates a score based on various factors:
#         - **High score** for finding a valid OTP format.
#         - **Bonus points** for keywords like 'verification', 'login', company names (Google, Axis Bank), and security warnings.
#     4.  **Classification**: If the final score is **50 or higher**, the message is classified as an OTP.

#     This method is more resilient to new and varied message formats and is much better at avoiding common false positives.
#     """)

# if __name__ == "__main__":
#     main()