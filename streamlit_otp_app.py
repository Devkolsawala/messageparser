import streamlit as st
import pandas as pd
import json
import io
from typing import Dict, List, Optional
import time
from datetime import datetime

# Import the OTP parser class
from parsing import EnhancedOTPMessageParser

def main():
    st.set_page_config(
        page_title="OTP Message Parser",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔐 OTP Message Parser")
    st.markdown("**Analyze SMS messages to identify and extract OTP information**")
    
    # Initialize parser
    if 'parser' not in st.session_state:
        st.session_state.parser = EnhancedOTPMessageParser()
    
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
    st.markdown("Analyze individual SMS messages for OTP content")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Input fields
        message_text = st.text_area(
            "Message Content",
            placeholder="Enter the SMS message text here...",
            height=150,
            help="Paste the complete SMS message text"
        )
        
        sender_name = st.text_input(
            "Sender Name (Optional)",
            placeholder="e.g., DM-DREAM11, PAYTM, JIO",
            help="The sender ID or name from the SMS"
        )
        
        analyze_btn = st.button("🔍 Analyze Message", type="primary")
    
    with col2:
        st.markdown("### Quick Test Examples")
        
        example_messages = {
            "Dream11 OTP": "676653 is the OTP for your Dream11 account. Do not share this with anyone.",
            "Paytm OTP": "Your OTP is 955980 ID: asasK/GTt2i. Paytm never calls you asking for OTP.",
            "Banking Alert": "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR",
            "Data Alert": "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517"
        }
        
        for label, example in example_messages.items():
            if st.button(f"Load: {label}", key=f"example_{label}"):
                st.session_state.example_message = example
                st.rerun()
        
        # Load example if selected
        if 'example_message' in st.session_state:
            message_text = st.session_state.example_message
            del st.session_state.example_message
    
    # Analysis results
    if analyze_btn and message_text.strip():
        with st.spinner("Analyzing message..."):
            # Get detailed analysis
            analysis = parser.analyze_single_message(message_text, sender_name)
            
            # Display results
            st.divider()
            st.subheader("📊 Analysis Results")
            
            # Main result
            result = analysis['final_result']
            confidence = analysis['confidence_score']
            
            if result['status'] == 'parsed':
                st.success(f"✅ **OTP Message Detected** (Confidence: {confidence}%)")
                
                # Display extracted information in columns
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("OTP Code", result.get('otp_code') or "Not found")
                    st.metric("Company", result.get('company_name') or "Unknown")
                
                with col2:
                    st.metric("Purpose", result.get('purpose') or "General")
                    st.metric("Validity", result.get('expiry_duration') or "Not specified")
                
                with col3:
                    st.metric("Reference ID", result.get('reference_id') or "None")
                    st.metric("Phone Number", result.get('phone_number') or "Not mentioned")
                
                # Additional information
                if result.get('security_warnings_text'):
                    st.info(f"🛡️ **Security Warning**: {result['security_warnings_text']}")
                
                if result.get('sender_name'):
                    st.info(f"📤 **Sender**: {result['sender_name']} ({result.get('sender_type')})")
            
            else:
                st.error(f"❌ **Not an OTP Message** (Confidence: {confidence}%)")
                st.warning(f"**Reason**: {result.get('reason')}")
            
            # Detailed analysis breakdown
            with st.expander("🔍 Detailed Analysis Breakdown"):
                st.markdown("### Analysis Steps")
                
                checks = analysis['analysis_steps']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Content Checks:**")
                    for check in ['has_otp_number', 'strong_otp_indicators', 'security_context', 'validity_context']:
                        status = "✅" if checks[check] else "❌"
                        label = check.replace('_', ' ').title()
                        st.markdown(f"{status} {label}")
                
                with col2:
                    st.markdown("**Exclusion Checks:**")
                    for check in ['banking_context', 'promotional_context']:
                        status = "⚠️" if checks[check] else "✅"
                        label = check.replace('_', ' ').title()
                        st.markdown(f"{status} {label} (should be False)")
                
                st.markdown(f"**Final Classification**: {'✅ True OTP' if checks['is_true_otp'] else '❌ Not OTP'}")
            
            # JSON output
            with st.expander("📄 Raw JSON Output"):
                st.json(result)

def csv_processing_interface(parser):
    st.header("📊 CSV File Processing")
    st.markdown("Upload and analyze CSV files containing SMS messages")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload CSV File",
        type=['csv'],
        help="CSV should contain a 'message' column and optionally a 'sender_name' column"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file, dtype=str)
            
            st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")
            
            # Display file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", f"{len(df):,}")
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
            
            # Check required columns
            required_cols = ['message']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                st.info("Your CSV must contain a 'message' column")
                return
            
            # Optional sender_name column
            if 'sender_name' not in df.columns:
                st.warning("⚠️ No 'sender_name' column found. Will proceed without sender information.")
                df['sender_name'] = ""
            
            # Show data preview
            st.subheader("📋 Data Preview")
            preview_rows = st.slider("Rows to preview", 5, min(20, len(df)), 10)
            st.dataframe(df.head(preview_rows))
            
            # Processing options
            st.subheader("⚙️ Processing Options")
            
            col1, col2 = st.columns(2)
            with col1:
                confidence_threshold = st.slider(
                    "Confidence Threshold", 
                    min_value=0, 
                    max_value=100, 
                    value=50,
                    help="Minimum confidence score to classify as OTP (default: 50)"
                )
            
            with col2:
                max_rows = st.number_input(
                    "Max Rows to Process", 
                    min_value=100, 
                    max_value=len(df), 
                    value=min(10000, len(df)),
                    help="Limit processing for large files"
                )
            
            # Process button
            if st.button("🚀 Process Messages", type="primary"):
                process_csv_data(parser, df, max_rows, confidence_threshold)
        
        except Exception as e:
            st.error(f"❌ Error reading CSV file: {str(e)}")
            st.info("Please ensure your file is a valid CSV format")

def process_csv_data(parser, df, max_rows, confidence_threshold):
    """Process CSV data and display results"""
    
    # Limit rows if needed
    if len(df) > max_rows:
        df_process = df.head(max_rows)
        st.warning(f"⚠️ Processing first {max_rows:,} rows only")
    else:
        df_process = df
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Results containers
    otp_messages = []
    rejected_messages = []
    
    total_rows = len(df_process)
    
    # Process in batches
    batch_size = 500
    start_time = time.time()
    
    for i in range(0, total_rows, batch_size):
        end_idx = min(i + batch_size, total_rows)
        
        # Process batch
        for idx in range(i, end_idx):
            row = df_process.iloc[idx]
            message = row['message'] if pd.notna(row['message']) else ""
            sender = row['sender_name'] if pd.notna(row['sender_name']) else ""
            
            # Parse message
            parsed_result = parser.parse_single_message(message, sender)
            parsed_result['original_index'] = idx
            
            # Apply confidence threshold
            if (parsed_result['status'] == 'parsed' and 
                parsed_result.get('confidence_score', 0) >= confidence_threshold):
                otp_messages.append(parsed_result)
            else:
                rejected_messages.append(parsed_result)
        
        # Update progress
        progress = end_idx / total_rows
        progress_bar.progress(progress)
        
        elapsed = time.time() - start_time
        rate = end_idx / elapsed if elapsed > 0 else 0
        
        status_text.text(
            f"Processed: {end_idx:,}/{total_rows:,} ({progress*100:.1f}%) | "
            f"Rate: {rate:.0f} msgs/sec | "
            f"OTP Found: {len(otp_messages):,}"
        )
    
    processing_time = time.time() - start_time
    
    # Display results
    st.success(f"✅ Processing completed in {processing_time:.1f} seconds!")
    
    # Summary metrics
    st.subheader("📈 Processing Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Processed", f"{total_rows:,}")
    with col2:
        st.metric("OTP Messages", f"{len(otp_messages):,}")
    with col3:
        st.metric("Rejected", f"{len(rejected_messages):,}")
    with col4:
        detection_rate = (len(otp_messages) / total_rows) * 100 if total_rows > 0 else 0
        st.metric("Detection Rate", f"{detection_rate:.2f}%")
    
    # Results tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 OTP Messages", "📊 Statistics", "❌ Rejected", "💾 Download"])
    
    with tab1:
        display_otp_messages(otp_messages)
    
    with tab2:
        display_statistics(otp_messages)
    
    with tab3:
        display_rejected_messages(rejected_messages)
    
    with tab4:
        display_download_options(otp_messages, rejected_messages, df_process)

def display_otp_messages(otp_messages):
    """Display parsed OTP messages"""
    
    if not otp_messages:
        st.info("No OTP messages found with the current settings")
        return
    
    st.markdown(f"### Found {len(otp_messages):,} OTP Messages")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    companies = sorted(set(msg.get('company_name') for msg in otp_messages if msg.get('company_name')))
    purposes = sorted(set(msg.get('purpose') for msg in otp_messages if msg.get('purpose')))
    
    with col1:
        company_filter = st.selectbox("Filter by Company", ["All"] + companies)
    
    with col2:
        purpose_filter = st.selectbox("Filter by Purpose", ["All"] + purposes)
    
    with col3:
        min_confidence = st.slider("Min Confidence", 0, 100, 50)
    
    # Apply filters
    filtered_messages = otp_messages
    
    if company_filter != "All":
        filtered_messages = [msg for msg in filtered_messages if msg.get('company_name') == company_filter]
    
    if purpose_filter != "All":
        filtered_messages = [msg for msg in filtered_messages if msg.get('purpose') == purpose_filter]
    
    filtered_messages = [msg for msg in filtered_messages if msg.get('confidence_score', 0) >= min_confidence]
    
    st.markdown(f"**Showing {len(filtered_messages):,} messages after filtering**")
    
    # Display messages
    for i, msg in enumerate(filtered_messages[:50]):  # Limit to first 50 for performance
        with st.expander(f"Message {i+1}: {msg.get('company_name', 'Unknown')} - {msg.get('otp_code', 'No OTP')}"):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Message Content:**")
                st.text(msg.get('raw_message', '')[:500] + ("..." if len(msg.get('raw_message', '')) > 500 else ""))
                
                if msg.get('sender_name'):
                    st.markdown(f"**Sender:** {msg['sender_name']} ({msg.get('sender_type', 'Unknown')})")
            
            with col2:
                st.markdown("**Extracted Information:**")
                
                info_items = [
                    ("OTP Code", msg.get('otp_code')),
                    ("Company", msg.get('company_name')),
                    ("Purpose", msg.get('purpose')),
                    ("Validity", msg.get('expiry_duration')),
                    ("Reference ID", msg.get('reference_id')),
                    ("Phone Number", msg.get('phone_number')),
                    ("Confidence", f"{msg.get('confidence_score', 0)}%")
                ]
                
                for label, value in info_items:
                    if value:
                        st.markdown(f"**{label}:** {value}")
                
                if msg.get('security_warnings_text'):
                    st.warning(f"🛡️ {msg['security_warnings_text']}")
    
    if len(filtered_messages) > 50:
        st.info(f"Showing first 50 messages. {len(filtered_messages) - 50} more messages available in download.")

def display_statistics(otp_messages):
    """Display statistical analysis of OTP messages"""
    
    if not otp_messages:
        st.info("No OTP messages to analyze")
        return
    
    st.subheader("📊 Statistical Analysis")
    
    # Generate statistics
    stats = generate_statistics(otp_messages)
    
    # Extraction rates
    st.markdown("### 📈 Extraction Success Rates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        extraction_data = stats['extraction_rates']
        for metric, rate in extraction_data.items():
            st.metric(metric.replace('_', ' ').title(), f"{rate}%")
    
    with col2:
        quality_data = stats['quality_metrics']
        st.metric("Average Confidence", f"{quality_data['average_confidence_score']}%")
        st.metric("High Confidence (≥80)", quality_data['high_confidence_messages'])
        st.metric("Medium Confidence (50-79)", quality_data['medium_confidence_messages'])
    
    # Distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏢 Top Companies")
        company_data = stats['distributions']['top_companies']
        if company_data:
            company_df = pd.DataFrame(
                list(company_data.items()),
                columns=['Company', 'Count']
            )
            st.bar_chart(company_df.set_index('Company'))
        else:
            st.info("No company data available")
    
    with col2:
        st.markdown("### 🎯 Purpose Distribution")
        purpose_data = stats['distributions']['purposes']
        if purpose_data:
            purpose_df = pd.DataFrame(
                list(purpose_data.items()),
                columns=['Purpose', 'Count']
            )
            st.bar_chart(purpose_df.set_index('Purpose'))
        else:
            st.info("No purpose data available")
    
    # Expiry analysis
    st.markdown("### ⏱️ Expiry Time Analysis")
    expiry_data = stats['distributions']['expiry_durations']
    if expiry_data:
        expiry_df = pd.DataFrame(
            list(expiry_data.items()),
            columns=['Duration', 'Count']
        )
        st.dataframe(expiry_df)
    else:
        st.info("No expiry information found in messages")

def display_rejected_messages(rejected_messages):
    """Display sample rejected messages"""
    
    if not rejected_messages:
        st.info("No rejected messages to display")
        return
    
    st.subheader("❌ Rejected Messages Sample")
    st.markdown(f"Showing sample of {min(10, len(rejected_messages))} rejected messages out of {len(rejected_messages):,} total")
    
    # Group by rejection reason
    reasons = {}
    for msg in rejected_messages[:50]:  # Analyze first 50 for grouping
        reason = msg.get('reason', 'Unknown')
        if reason not in reasons:
            reasons[reason] = []
        reasons[reason].append(msg)
    
    for reason, msgs in reasons.items():
        with st.expander(f"{reason} ({len(msgs)} messages)"):
            for i, msg in enumerate(msgs[:3]):  # Show max 3 examples per reason
                st.markdown(f"**Example {i+1}:**")
                st.text(msg.get('message_preview', ''))
                st.markdown(f"*Confidence: {msg.get('confidence_score', 0)}%*")
                st.divider()

def display_download_options(otp_messages, rejected_messages, original_df):
    """Provide download options for results"""
    
    st.subheader("💾 Download Results")
    
    # Prepare download data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📄 JSON Format")
        
        # Complete results
        complete_results = {
            'metadata': {
                'processed_at': datetime.now().isoformat(),
                'total_messages': len(original_df),
                'otp_messages_found': len(otp_messages),
                'rejected_messages': len(rejected_messages),
                'detection_rate': round((len(otp_messages) / len(original_df)) * 100, 2) if len(original_df) > 0 else 0
            },
            'otp_messages': otp_messages,
            'rejected_sample': rejected_messages[:100]  # Sample of rejected messages
        }
        
        if st.button("📥 Download Complete JSON Results"):
            json_str = json.dumps(complete_results, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"otp_analysis_results_{timestamp}.json",
                mime="application/json"
            )
    
    with col2:
        st.markdown("### 📊 CSV Format")
        
        if otp_messages:
            # Create CSV from OTP messages
            otp_df = pd.DataFrame(otp_messages)
            
            # Select relevant columns for CSV
            csv_columns = [
                'otp_code', 'company_name', 'purpose', 'expiry_duration',
                'sender_name', 'confidence_score', 'reference_id', 
                'phone_number', 'security_warnings_text', 'raw_message'
            ]
            
            csv_df = otp_df[[col for col in csv_columns if col in otp_df.columns]]
            
            csv_buffer = io.StringIO()
            csv_df.to_csv(csv_buffer, index=False)
            
            if st.button("📥 Download OTP Messages CSV"):
                st.download_button(
                    label="Download CSV", 
                    data=csv_buffer.getvalue(),
                    file_name=f"otp_messages_{timestamp}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No OTP messages found to export")
    
    # Statistics summary
    if otp_messages:
        st.markdown("### 📋 Summary Report")
        
        stats = generate_statistics(otp_messages)
        
        summary_text = f"""
# OTP Analysis Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Results
- Total Messages Processed: {len(original_df):,}
- OTP Messages Found: {len(otp_messages):,}
- Detection Rate: {stats['quality_metrics']['average_confidence_score']}%

## Top Companies
{chr(10).join(f"- {company}: {count}" for company, count in list(stats['distributions']['top_companies'].items())[:5])}

## Extraction Success Rates
{chr(10).join(f"- {metric.replace('_', ' ').title()}: {rate}%" for metric, rate in stats['extraction_rates'].items())}
        """
        
        if st.button("📥 Download Summary Report"):
            st.download_button(
                label="Download Report",
                data=summary_text,
                file_name=f"otp_analysis_summary_{timestamp}.txt",
                mime="text/plain"
            )

def generate_statistics(otp_messages):
    """Generate statistics for OTP messages"""
    
    if not otp_messages:
        return {}
    
    total_otp = len(otp_messages)
    
    # Calculate extraction rates
    extraction_rates = {
        'otp_codes_extracted': round((sum(1 for msg in otp_messages if msg.get('otp_code')) / total_otp) * 100, 2),
        'companies_identified': round((sum(1 for msg in otp_messages if msg.get('company_name')) / total_otp) * 100, 2),
        'purposes_identified': round((sum(1 for msg in otp_messages if msg.get('purpose')) / total_otp) * 100, 2),
        'expiry_info_found': round((sum(1 for msg in otp_messages if msg.get('expiry_info')) / total_otp) * 100, 2),
    }
    
    # Distribution analysis
    companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
    company_counts = {}
    for company in companies:
        company_counts[company] = company_counts.get(company, 0) + 1
    
    purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
    purpose_counts = {}
    for purpose in purposes:
        purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
    
    expiry_durations = [msg.get('expiry_duration') for msg in otp_messages if msg.get('expiry_duration')]
    expiry_counts = {}
    for duration in expiry_durations:
        expiry_counts[duration] = expiry_counts.get(duration, 0) + 1
    
    # Quality metrics
    confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    quality_metrics = {
        'average_confidence_score': round(avg_confidence, 2),
        'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
        'medium_confidence_messages': sum(1 for score in confidence_scores if 50 <= score < 80),
        'low_confidence_messages': sum(1 for score in confidence_scores if score < 50),
    }
    
    return {
        'extraction_rates': extraction_rates,
        'distributions': {
            'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)),
            'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
            'expiry_durations': dict(sorted(expiry_counts.items(), key=lambda x: x[1], reverse=True)),
        },
        'quality_metrics': quality_metrics
    }

def about_page():
    """Display about page with parser information"""
    
    st.header("ℹ️ About OTP Message Parser")
    
    st.markdown("""
    ### What is this tool?
    
    The OTP Message Parser is an advanced tool designed to analyze SMS messages and identify 
    One-Time Password (OTP) content with high accuracy. It uses sophisticated pattern matching, 
    keyword analysis, and machine learning techniques to distinguish genuine OTP messages from 
    other types of SMS content.
    
    ### Key Features
    
    - **Smart Classification**: Uses multiple algorithms to accurately identify OTP messages
    - **Information Extraction**: Extracts OTP codes, company names, purposes, and expiry times
    - **Confidence Scoring**: Provides confidence scores for each classification
    - **Batch Processing**: Efficiently processes large CSV files
    - **Real-time Analysis**: Analyze individual messages instantly
    - **Export Options**: Download results in JSON or CSV format
    
    ### How It Works
    
    1. **Pattern Matching**: Uses regex patterns to identify OTP-specific language
    2. **Context Analysis**: Considers security warnings, validity periods, and company mentions
    3. **Exclusion Rules**: Filters out banking alerts, promotional messages, and notifications
    4. **Confidence Scoring**: Assigns confidence scores based on multiple factors
    5. **Smart Extraction**: Extracts structured information from unstructured text
    
    ### Supported Message Types
    
    - Login/Registration OTPs
    - Transaction verification codes
    - Account verification messages
    - Password reset codes
    - Service-specific OTPs (Dream11, Paytm, PhonePe, etc.)
    
    ### CSV File Requirements
    
    Your CSV file should contain:
    - **Required**: `message` column with SMS text
    - **Optional**: `sender_name` column with sender information
    
    ### Confidence Threshold
    
    - **50-79**: Medium confidence (may include some false positives)
    - **80-100**: High confidence (very likely genuine OTPs)
    - **Default**: 50 (balanced accuracy)
    """)
    
    st.markdown("### 🔧 Technical Details")
    
    with st.expander("Pattern Categories"):
        st.markdown("""
        **OTP Detection Patterns:**
        - Direct OTP statements: "123456 is your OTP"
        - OTP requests: "Enter OTP 123456"
        - Company-specific formats: "Your Paytm OTP is 123456"
        
        **Exclusion Patterns:**
        - Banking transactions: "Credited by Rs. 1000"
        - Data usage alerts: "90% quota used"
        - Promotional content: "Register for webinar"
        """)
    
    with st.expander("Supported Companies"):
        companies = [
            "Dream11", "Paytm", "PhonePe", "Zupee", "Meesho", "AJIO",
            "Google Pay", "Amazon", "Flipkart", "Myntra", "Swiggy", "Zomato",
            "Ola", "Uber", "BigBasket", "BookMyShow", "MakeMyTrip",
            "ICICI Bank", "HDFC", "SBI", "Axis Bank", "Jio", "Airtel", "Vi",
            "WhatsApp", "Facebook", "Instagram"
        ]
        
        cols = st.columns(4)
        for i, company in enumerate(companies):
            with cols[i % 4]:
                st.markdown(f"• {company}")

if __name__ == "__main__":
    main()


























# import streamlit as st
# import pandas as pd
# import json
# import io
# from typing import Dict, List, Optional
# import time
# from datetime import datetime

# # Import the OTP parser class
# from parsing import EnhancedOTPMessageParser

# def main():
#     st.set_page_config(
#         page_title="OTP Message Parser",
#         page_icon="🔐",
#         layout="wide",
#         initial_sidebar_state="expanded"
#     )
    
#     st.title("🔐 OTP Message Parser")
#     st.markdown("**Analyze SMS messages to identify and extract OTP information**")
    
#     # Initialize parser
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
#     st.markdown("Analyze individual SMS messages for OTP content")
    
#     col1, col2 = st.columns([2, 1])
    
#     with col1:
#         # Input fields
#         message_text = st.text_area(
#             "Message Content",
#             placeholder="Enter the SMS message text here...",
#             height=150,
#             help="Paste the complete SMS message text"
#         )
        
#         sender_name = st.text_input(
#             "Sender Name (Optional)",
#             placeholder="e.g., DM-DREAM11, PAYTM, JIO",
#             help="The sender ID or name from the SMS"
#         )
        
#         analyze_btn = st.button("🔍 Analyze Message", type="primary")
    
#     with col2:
#         st.markdown("### Quick Test Examples")
        
#         example_messages = {
#             "Dream11 OTP": "676653 is the OTP for your Dream11 account. Do not share this with anyone.",
#             "Paytm OTP": "Your OTP is 955980 ID: asasK/GTt2i. Paytm never calls you asking for OTP.",
#             "Banking Alert": "A/c 5XXXXX5410 credited by Rs. 47,614 Total Bal: Rs. 47,695.00 CR",
#             "Data Alert": "90% daily data quota used as on 05-Aug-24 23:45. Jio Number : 9399843517"
#         }
        
#         for label, example in example_messages.items():
#             if st.button(f"Load: {label}", key=f"example_{label}"):
#                 st.session_state.example_message = example
#                 st.rerun()
        
#         # Load example if selected
#         if 'example_message' in st.session_state:
#             message_text = st.session_state.example_message
#             del st.session_state.example_message
    
#     # Analysis results
#     if analyze_btn and message_text.strip():
#         with st.spinner("Analyzing message..."):
#             # Get detailed analysis
#             analysis = parser.analyze_single_message(message_text, sender_name)
            
#             # Display results
#             st.divider()
#             st.subheader("📊 Analysis Results")
            
#             # Main result
#             result = analysis['final_result']
#             confidence = analysis['confidence_score']
            
#             if result['status'] == 'parsed':
#                 st.success(f"✅ **OTP Message Detected** (Confidence: {confidence}%)")
                
#                 # Display extracted information in columns
#                 col1, col2, col3 = st.columns(3)
                
#                 with col1:
#                     st.metric("OTP Code", result.get('otp_code') or "Not found")
#                     st.metric("Company", result.get('company_name') or "Unknown")
                
#                 with col2:
#                     st.metric("Purpose", result.get('purpose') or "General")
#                     st.metric("Validity", result.get('expiry_duration') or "Not specified")
                
#                 with col3:
#                     st.metric("Reference ID", result.get('reference_id') or "None")
#                     st.metric("Phone Number", result.get('phone_number') or "Not mentioned")
                
#                 # Additional information
#                 if result.get('security_warnings_text'):
#                     st.info(f"🛡️ **Security Warning**: {result['security_warnings_text']}")
                
#                 if result.get('sender_name'):
#                     st.info(f"📤 **Sender**: {result['sender_name']} ({result.get('sender_type')})")
            
#             else:
#                 st.error(f"❌ **Not an OTP Message** (Confidence: {confidence}%)")
#                 st.warning(f"**Reason**: {result.get('reason')}")
            
#             # Detailed analysis breakdown
#             with st.expander("🔍 Detailed Analysis Breakdown"):
#                 st.markdown("### Analysis Steps")
                
#                 checks = analysis['analysis_steps']
                
#                 col1, col2 = st.columns(2)
                
#                 with col1:
#                     st.markdown("**Content Checks:**")
#                     for check in ['has_otp_number', 'strong_otp_indicators', 'security_context', 'validity_context']:
#                         status = "✅" if checks[check] else "❌"
#                         label = check.replace('_', ' ').title()
#                         st.markdown(f"{status} {label}")
                
#                 with col2:
#                     st.markdown("**Exclusion Checks:**")
#                     for check in ['banking_context', 'promotional_context']:
#                         status = "⚠️" if checks[check] else "✅"
#                         label = check.replace('_', ' ').title()
#                         st.markdown(f"{status} {label} (should be False)")
                
#                 st.markdown(f"**Final Classification**: {'✅ True OTP' if checks['is_true_otp'] else '❌ Not OTP'}")
            
#             # JSON output
#             with st.expander("📄 Raw JSON Output"):
#                 st.json(result)

# def csv_processing_interface(parser):
#     st.header("📊 CSV File Processing")
#     st.markdown("Upload and analyze CSV files containing SMS messages")
    
#     # File upload
#     uploaded_file = st.file_uploader(
#         "Upload CSV File",
#         type=['csv'],
#         help="CSV should contain a 'message' column and optionally a 'sender_name' column"
#     )
    
#     if uploaded_file is not None:
#         try:
#             # Read CSV
#             df = pd.read_csv(uploaded_file, dtype=str)
            
#             st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")
            
#             # Display file info
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 st.metric("Total Rows", f"{len(df):,}")
#             with col2:
#                 st.metric("Columns", len(df.columns))
#             with col3:
#                 st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
            
#             # Check required columns
#             required_cols = ['message']
#             missing_cols = [col for col in required_cols if col not in df.columns]
            
#             if missing_cols:
#                 st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
#                 st.info("Your CSV must contain a 'message' column")
#                 return
            
#             # Optional sender_name column
#             if 'sender_name' not in df.columns:
#                 st.warning("⚠️ No 'sender_name' column found. Will proceed without sender information.")
#                 df['sender_name'] = ""
            
#             # Show data preview
#             st.subheader("📋 Data Preview")
#             preview_rows = st.slider("Rows to preview", 5, min(20, len(df)), 10)
#             st.dataframe(df.head(preview_rows))
            
#             # Processing options
#             st.subheader("⚙️ Processing Options")
            
#             col1, col2 = st.columns(2)
#             with col1:
#                 confidence_threshold = st.slider(
#                     "Confidence Threshold", 
#                     min_value=0, 
#                     max_value=100, 
#                     value=60,
#                     help="Minimum confidence score to classify as OTP (default: 40)"
#                 )
            
#             with col2:
#                 max_rows = st.number_input(
#                     "Max Rows to Process", 
#                     min_value=100, 
#                     max_value=len(df), 
#                     value=min(10000, len(df)),
#                     help="Limit processing for large files"
#                 )
            
#             # Process button
#             if st.button("🚀 Process Messages", type="primary"):
#                 process_csv_data(parser, df, max_rows, confidence_threshold)
        
#         except Exception as e:
#             st.error(f"❌ Error reading CSV file: {str(e)}")
#             st.info("Please ensure your file is a valid CSV format")

# def process_csv_data(parser, df, max_rows, confidence_threshold):
#     """Process CSV data and display results"""
    
#     # Limit rows if needed
#     if len(df) > max_rows:
#         df_process = df.head(max_rows)
#         st.warning(f"⚠️ Processing first {max_rows:,} rows only")
#     else:
#         df_process = df
    
#     # Progress tracking
#     progress_bar = st.progress(0)
#     status_text = st.empty()
    
#     # Results containers
#     otp_messages = []
#     rejected_messages = []
    
#     total_rows = len(df_process)
    
#     # Process in batches
#     batch_size = 500
#     start_time = time.time()
    
#     for i in range(0, total_rows, batch_size):
#         end_idx = min(i + batch_size, total_rows)
        
#         # Process batch
#         for idx in range(i, end_idx):
#             row = df_process.iloc[idx]
#             message = row['message'] if pd.notna(row['message']) else ""
#             sender = row['sender_name'] if pd.notna(row['sender_name']) else ""
            
#             # Parse message
#             parsed_result = parser.parse_single_message(message, sender)
#             parsed_result['original_index'] = idx
            
#             # Apply confidence threshold
#             if (parsed_result['status'] == 'parsed' and 
#                 parsed_result.get('confidence_score', 0) >= confidence_threshold):
#                 otp_messages.append(parsed_result)
#             else:
#                 rejected_messages.append(parsed_result)
        
#         # Update progress
#         progress = end_idx / total_rows
#         progress_bar.progress(progress)
        
#         elapsed = time.time() - start_time
#         rate = end_idx / elapsed if elapsed > 0 else 0
        
#         status_text.text(
#             f"Processed: {end_idx:,}/{total_rows:,} ({progress*100:.1f}%) | "
#             f"Rate: {rate:.0f} msgs/sec | "
#             f"OTP Found: {len(otp_messages):,}"
#         )
    
#     processing_time = time.time() - start_time
    
#     # Display results
#     st.success(f"✅ Processing completed in {processing_time:.1f} seconds!")
    
#     # Summary metrics
#     st.subheader("📈 Processing Summary")
    
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.metric("Total Processed", f"{total_rows:,}")
#     with col2:
#         st.metric("OTP Messages", f"{len(otp_messages):,}")
#     with col3:
#         st.metric("Rejected", f"{len(rejected_messages):,}")
#     with col4:
#         detection_rate = (len(otp_messages) / total_rows) * 100 if total_rows > 0 else 0
#         st.metric("Detection Rate", f"{detection_rate:.2f}%")
    
#     # Results tabs
#     tab1, tab2, tab3, tab4 = st.tabs(["📋 OTP Messages", "📊 Statistics", "❌ Rejected", "💾 Download"])
    
#     with tab1:
#         display_otp_messages(otp_messages)
    
#     with tab2:
#         display_statistics(otp_messages)
    
#     with tab3:
#         display_rejected_messages(rejected_messages)
    
#     with tab4:
#         display_download_options(otp_messages, rejected_messages, df_process)

# def display_otp_messages(otp_messages):
#     """Display parsed OTP messages"""
    
#     if not otp_messages:
#         st.info("No OTP messages found with the current settings")
#         return
    
#     st.markdown(f"### Found {len(otp_messages):,} OTP Messages")
    
#     # Filters
#     col1, col2, col3 = st.columns(3)
    
#     companies = sorted(set(msg.get('company_name') for msg in otp_messages if msg.get('company_name')))
#     purposes = sorted(set(msg.get('purpose') for msg in otp_messages if msg.get('purpose')))
    
#     with col1:
#         company_filter = st.selectbox("Filter by Company", ["All"] + companies)
    
#     with col2:
#         purpose_filter = st.selectbox("Filter by Purpose", ["All"] + purposes)
    
#     with col3:
#         min_confidence = st.slider("Min Confidence", 0, 100, 60)
    
#     # Apply filters
#     filtered_messages = otp_messages
    
#     if company_filter != "All":
#         filtered_messages = [msg for msg in filtered_messages if msg.get('company_name') == company_filter]
    
#     if purpose_filter != "All":
#         filtered_messages = [msg for msg in filtered_messages if msg.get('purpose') == purpose_filter]
    
#     filtered_messages = [msg for msg in filtered_messages if msg.get('confidence_score', 0) >= min_confidence]
    
#     st.markdown(f"**Showing {len(filtered_messages):,} messages after filtering**")
    
#     # Display messages
#     for i, msg in enumerate(filtered_messages[:50]):  # Limit to first 50 for performance
#         with st.expander(f"Message {i+1}: {msg.get('company_name', 'Unknown')} - {msg.get('otp_code', 'No OTP')}"):
            
#             col1, col2 = st.columns([2, 1])
            
#             with col1:
#                 st.markdown("**Message Content:**")
#                 st.text(msg.get('raw_message', '')[:500] + ("..." if len(msg.get('raw_message', '')) > 500 else ""))
                
#                 if msg.get('sender_name'):
#                     st.markdown(f"**Sender:** {msg['sender_name']} ({msg.get('sender_type', 'Unknown')})")
            
#             with col2:
#                 st.markdown("**Extracted Information:**")
                
#                 info_items = [
#                     ("OTP Code", msg.get('otp_code')),
#                     ("Company", msg.get('company_name')),
#                     ("Purpose", msg.get('purpose')),
#                     ("Validity", msg.get('expiry_duration')),
#                     ("Reference ID", msg.get('reference_id')),
#                     ("Phone Number", msg.get('phone_number')),
#                     ("Confidence", f"{msg.get('confidence_score', 0)}%")
#                 ]
                
#                 for label, value in info_items:
#                     if value:
#                         st.markdown(f"**{label}:** {value}")
                
#                 if msg.get('security_warnings_text'):
#                     st.warning(f"🛡️ {msg['security_warnings_text']}")
    
#     if len(filtered_messages) > 50:
#         st.info(f"Showing first 50 messages. {len(filtered_messages) - 50} more messages available in download.")

# def display_statistics(otp_messages):
#     """Display statistical analysis of OTP messages"""
    
#     if not otp_messages:
#         st.info("No OTP messages to analyze")
#         return
    
#     st.subheader("📊 Statistical Analysis")
    
#     # Generate statistics
#     stats = generate_statistics(otp_messages)
    
#     # Extraction rates
#     st.markdown("### 📈 Extraction Success Rates")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         extraction_data = stats['extraction_rates']
#         for metric, rate in extraction_data.items():
#             st.metric(metric.replace('_', ' ').title(), f"{rate}%")
    
#     with col2:
#         quality_data = stats['quality_metrics']
#         st.metric("Average Confidence", f"{quality_data['average_confidence_score']}%")
#         st.metric("High Confidence (≥80)", quality_data['high_confidence_messages'])
#         st.metric("Medium Confidence (60-79)", quality_data['medium_confidence_messages'])
    
#     # Distribution charts
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown("### 🏢 Top Companies")
#         company_data = stats['distributions']['top_companies']
#         if company_data:
#             company_df = pd.DataFrame(
#                 list(company_data.items()),
#                 columns=['Company', 'Count']
#             )
#             st.bar_chart(company_df.set_index('Company'))
#         else:
#             st.info("No company data available")
    
#     with col2:
#         st.markdown("### 🎯 Purpose Distribution")
#         purpose_data = stats['distributions']['purposes']
#         if purpose_data:
#             purpose_df = pd.DataFrame(
#                 list(purpose_data.items()),
#                 columns=['Purpose', 'Count']
#             )
#             st.bar_chart(purpose_df.set_index('Purpose'))
#         else:
#             st.info("No purpose data available")
    
#     # Expiry analysis
#     st.markdown("### ⏱️ Expiry Time Analysis")
#     expiry_data = stats['distributions']['expiry_durations']
#     if expiry_data:
#         expiry_df = pd.DataFrame(
#             list(expiry_data.items()),
#             columns=['Duration', 'Count']
#         )
#         st.dataframe(expiry_df)
#     else:
#         st.info("No expiry information found in messages")

# def display_rejected_messages(rejected_messages):
#     """Display sample rejected messages"""
    
#     if not rejected_messages:
#         st.info("No rejected messages to display")
#         return
    
#     st.subheader("❌ Rejected Messages Sample")
#     st.markdown(f"Showing sample of {min(10, len(rejected_messages))} rejected messages out of {len(rejected_messages):,} total")
    
#     # Group by rejection reason
#     reasons = {}
#     for msg in rejected_messages[:50]:  # Analyze first 50 for grouping
#         reason = msg.get('reason', 'Unknown')
#         if reason not in reasons:
#             reasons[reason] = []
#         reasons[reason].append(msg)
    
#     for reason, msgs in reasons.items():
#         with st.expander(f"{reason} ({len(msgs)} messages)"):
#             for i, msg in enumerate(msgs[:3]):  # Show max 3 examples per reason
#                 st.markdown(f"**Example {i+1}:**")
#                 st.text(msg.get('message_preview', ''))
#                 st.markdown(f"*Confidence: {msg.get('confidence_score', 0)}%*")
#                 st.divider()

# def display_download_options(otp_messages, rejected_messages, original_df):
#     """Provide download options for results"""
    
#     st.subheader("💾 Download Results")
    
#     # Prepare download data
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.markdown("### 📄 JSON Format")
        
#         # Complete results
#         complete_results = {
#             'metadata': {
#                 'processed_at': datetime.now().isoformat(),
#                 'total_messages': len(original_df),
#                 'otp_messages_found': len(otp_messages),
#                 'rejected_messages': len(rejected_messages),
#                 'detection_rate': round((len(otp_messages) / len(original_df)) * 100, 2) if len(original_df) > 0 else 0
#             },
#             'otp_messages': otp_messages,
#             'rejected_sample': rejected_messages[:100]  # Sample of rejected messages
#         }
        
#         if st.button("📥 Download Complete JSON Results"):
#             json_str = json.dumps(complete_results, indent=2, ensure_ascii=False)
#             st.download_button(
#                 label="Download JSON",
#                 data=json_str,
#                 file_name=f"otp_analysis_results_{timestamp}.json",
#                 mime="application/json"
#             )
    
#     with col2:
#         st.markdown("### 📊 CSV Format")
        
#         if otp_messages:
#             # Create CSV from OTP messages
#             otp_df = pd.DataFrame(otp_messages)
            
#             # Select relevant columns for CSV
#             csv_columns = [
#                 'otp_code', 'company_name', 'purpose', 'expiry_duration',
#                 'sender_name', 'confidence_score', 'reference_id', 
#                 'phone_number', 'security_warnings_text', 'raw_message'
#             ]
            
#             csv_df = otp_df[[col for col in csv_columns if col in otp_df.columns]]
            
#             csv_buffer = io.StringIO()
#             csv_df.to_csv(csv_buffer, index=False)
            
#             if st.button("📥 Download OTP Messages CSV"):
#                 st.download_button(
#                     label="Download CSV", 
#                     data=csv_buffer.getvalue(),
#                     file_name=f"otp_messages_{timestamp}.csv",
#                     mime="text/csv"
#                 )
#         else:
#             st.info("No OTP messages found to export")
    
#     # Statistics summary
#     if otp_messages:
#         st.markdown("### 📋 Summary Report")
        
#         stats = generate_statistics(otp_messages)
        
#         summary_text = f"""
# # OTP Analysis Summary Report
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# ## Overall Results
# - Total Messages Processed: {len(original_df):,}
# - OTP Messages Found: {len(otp_messages):,}
# - Detection Rate: {stats['quality_metrics']['average_confidence_score']}%

# ## Top Companies
# {chr(10).join(f"- {company}: {count}" for company, count in list(stats['distributions']['top_companies'].items())[:5])}

# ## Extraction Success Rates
# {chr(10).join(f"- {metric.replace('_', ' ').title()}: {rate}%" for metric, rate in stats['extraction_rates'].items())}
#         """
        
#         if st.button("📥 Download Summary Report"):
#             st.download_button(
#                 label="Download Report",
#                 data=summary_text,
#                 file_name=f"otp_analysis_summary_{timestamp}.txt",
#                 mime="text/plain"
#             )

# def generate_statistics(otp_messages):
#     """Generate statistics for OTP messages"""
    
#     if not otp_messages:
#         return {}
    
#     total_otp = len(otp_messages)
    
#     # Calculate extraction rates
#     extraction_rates = {
#         'otp_codes_extracted': round((sum(1 for msg in otp_messages if msg.get('otp_code')) / total_otp) * 100, 2),
#         'companies_identified': round((sum(1 for msg in otp_messages if msg.get('company_name')) / total_otp) * 100, 2),
#         'purposes_identified': round((sum(1 for msg in otp_messages if msg.get('purpose')) / total_otp) * 100, 2),
#         'expiry_info_found': round((sum(1 for msg in otp_messages if msg.get('expiry_info')) / total_otp) * 100, 2),
#     }
    
#     # Distribution analysis
#     companies = [msg.get('company_name') for msg in otp_messages if msg.get('company_name')]
#     company_counts = {}
#     for company in companies:
#         company_counts[company] = company_counts.get(company, 0) + 1
    
#     purposes = [msg.get('purpose') for msg in otp_messages if msg.get('purpose')]
#     purpose_counts = {}
#     for purpose in purposes:
#         purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
    
#     expiry_durations = [msg.get('expiry_duration') for msg in otp_messages if msg.get('expiry_duration')]
#     expiry_counts = {}
#     for duration in expiry_durations:
#         expiry_counts[duration] = expiry_counts.get(duration, 0) + 1
    
#     # Quality metrics
#     confidence_scores = [msg.get('confidence_score', 0) for msg in otp_messages]
#     avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
#     quality_metrics = {
#         'average_confidence_score': round(avg_confidence, 2),
#         'high_confidence_messages': sum(1 for score in confidence_scores if score >= 80),
#         'medium_confidence_messages': sum(1 for score in confidence_scores if 60 <= score < 80),
#         'low_confidence_messages': sum(1 for score in confidence_scores if score < 60),
#     }
    
#     return {
#         'extraction_rates': extraction_rates,
#         'distributions': {
#             'top_companies': dict(sorted(company_counts.items(), key=lambda x: x[1], reverse=True)),
#             'purposes': dict(sorted(purpose_counts.items(), key=lambda x: x[1], reverse=True)),
#             'expiry_durations': dict(sorted(expiry_counts.items(), key=lambda x: x[1], reverse=True)),
#         },
#         'quality_metrics': quality_metrics
#     }

# def about_page():
#     """Display about page with parser information"""
    
#     st.header("ℹ️ About OTP Message Parser")
    
#     st.markdown("""
#     ### What is this tool?
    
#     The OTP Message Parser is an advanced tool designed to analyze SMS messages and identify 
#     One-Time Password (OTP) content with high accuracy. It uses sophisticated pattern matching, 
#     keyword analysis, and machine learning techniques to distinguish genuine OTP messages from 
#     other types of SMS content.
    
#     ### Key Features
    
#     - **Smart Classification**: Uses multiple algorithms to accurately identify OTP messages
#     - **Information Extraction**: Extracts OTP codes, company names, purposes, and expiry times
#     - **Confidence Scoring**: Provides confidence scores for each classification
#     - **Batch Processing**: Efficiently processes large CSV files
#     - **Real-time Analysis**: Analyze individual messages instantly
#     - **Export Options**: Download results in JSON or CSV format
    
#     ### How It Works
    
#     1. **Pattern Matching**: Uses regex patterns to identify OTP-specific language
#     2. **Context Analysis**: Considers security warnings, validity periods, and company mentions
#     3. **Exclusion Rules**: Filters out banking alerts, promotional messages, and notifications
#     4. **Confidence Scoring**: Assigns confidence scores based on multiple factors
#     5. **Smart Extraction**: Extracts structured information from unstructured text
    
#     ### Supported Message Types
    
#     - Login/Registration OTPs
#     - Transaction verification codes
#     - Account verification messages
#     - Password reset codes
#     - Service-specific OTPs (Dream11, Paytm, PhonePe, etc.)
    
#     ### CSV File Requirements
    
#     Your CSV file should contain:
#     - **Required**: `message` column with SMS text
#     - **Optional**: `sender_name` column with sender information
    
#     ### Confidence Threshold
    
#     - **60-79**: Medium confidence (may include some false positives)
#     - **80-100**: High confidence (very likely genuine OTPs)
#     - **Default**: 60 (balanced accuracy)
#     """)
    
#     st.markdown("### 🔧 Technical Details")
    
#     with st.expander("Pattern Categories"):
#         st.markdown("""
#         **OTP Detection Patterns:**
#         - Direct OTP statements: "123456 is your OTP"
#         - OTP requests: "Enter OTP 123456"
#         - Company-specific formats: "Your Paytm OTP is 123456"
        
#         **Exclusion Patterns:**
#         - Banking transactions: "Credited by Rs. 1000"
#         - Data usage alerts: "90% quota used"
#         - Promotional content: "Register for webinar"
#         """)
    
#     with st.expander("Supported Companies"):
#         companies = [
#             "Dream11", "Paytm", "PhonePe", "Zupee", "Meesho", "AJIO",
#             "Google Pay", "Amazon", "Flipkart", "Myntra", "Swiggy", "Zomato",
#             "Ola", "Uber", "BigBasket", "BookMyShow", "MakeMyTrip",
#             "ICICI Bank", "HDFC", "SBI", "Axis Bank", "Jio", "Airtel", "Vi",
#             "WhatsApp", "Facebook", "Instagram"
#         ]
        
#         cols = st.columns(4)
#         for i, company in enumerate(companies):
#             with cols[i % 4]:
#                 st.markdown(f"• {company}")

# if __name__ == "__main__":
#     main()