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
        ["Single Message Analysis", "CSV File Processing"]
    )
    
    if mode == "Single Message Analysis":
        single_message_interface(parser)
    elif mode == "CSV File Processing":
        csv_processing_interface(parser)
  

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



def main_app():
    main()

if __name__ == "__main__":
    main_app()