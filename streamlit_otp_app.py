import streamlit as st
import pandas as pd
import json
from enhanced_parsing import EnhancedMessageParser  # Import the updated parser
import time

# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="Enhanced Message Parser",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Main App Logic ---

# Initialize the parser
@st.cache_resource
def get_parser():
    """Load and cache the parser instance."""
    return EnhancedMessageParser()

parser = get_parser()

# --- UI Components ---

# 1. Title and Sidebar
st.title("🤖 Enhanced Message Parser v14.0")
st.markdown("A comprehensive tool to parse and analyze various types of SMS messages, including OTPs, EMIs, Challans, Transportation, EPF, E-commerce, and **Electricity Bills**.")

st.sidebar.header("📊 Parser Dashboard")
st.sidebar.markdown("Upload your CSV file and select the message type to begin analysis.")

# 2. File Uploader and Options
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])
message_type_options = ["auto", "otp", "emi", "challan", "transportation", "epf", "ecommerce", "electricity"]
selected_message_type = st.sidebar.selectbox("Select Message Type", message_type_options, index=0)

if uploaded_file is not None:
    st.sidebar.info(f"File '{uploaded_file.name}' uploaded successfully.")
    
    if st.sidebar.button("Process File", use_container_width=True):
        with st.spinner("Analyzing messages... This may take a few minutes for large files."):
            start_time = time.time()
            
            # Use a placeholder for live progress updates
            progress_placeholder = st.empty()
            
            try:
                # --- Main processing call ---
                results = parser.process_csv_file(uploaded_file, message_type=selected_message_type)
                
                processing_time = time.time() - start_time
                progress_placeholder.success(f"Analysis complete in {processing_time:.2f} seconds!")
                
                if results:
                    st.session_state['parsing_results'] = results
                else:
                    st.error("An error occurred during file processing. Please check the file format.")

            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- Display Results ---
if 'parsing_results' in st.session_state:
    results = st.session_state['parsing_results']
    metadata = results.get('metadata', {})
    
    st.header("📈 Parsing Summary")
    
    # --- Key Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Messages", f"{metadata.get('total_input_messages', 0):,}")
    col2.metric("Parsed Messages", f"{metadata.get('total_parsed_messages', 0):,}")
    col3.metric("Rejected Messages", f"{metadata.get('rejected_messages', 0):,}")
    col4.metric("Detection Rate", f"{metadata.get('detection_rate', 0)}%")

    # --- Message Type Breakdown ---
    st.subheader("Message Type Breakdown")
    otp_messages = results.get('otp_messages', [])
    emi_messages = results.get('emi_messages', [])
    challan_messages = results.get('challan_messages', [])
    transport_messages = results.get('transportation_messages', [])
    epf_messages = results.get('epf_messages', [])
    ecommerce_messages = results.get('ecommerce_messages', [])
    electricity_messages = results.get('electricity_messages', []) # NEW

    cols = st.columns(7)
    cols[0].metric("OTP Msgs", len(otp_messages))
    cols[1].metric("EMI Msgs", len(emi_messages))
    cols[2].metric("Challan Msgs", len(challan_messages))
    cols[3].metric("Transport Msgs", len(transport_messages))
    cols[4].metric("EPF Msgs", len(epf_messages))
    cols[5].metric("E-commerce Msgs", len(ecommerce_messages))
    cols[6].metric("Electricity Bills", len(electricity_messages)) # NEW

    st.markdown("---")

    # --- Detailed Expanders for each message type ---
    
    # OTP Messages
    if otp_messages:
        with st.expander(f"🔑 Parsed OTP Messages ({len(otp_messages)})", expanded=False):
            st.subheader("OTP Statistics")
            otp_stats = results.get('summary_statistics', {}).get('otp_stats', {})
            st.json(otp_stats)
            
            st.subheader("Parsed Data")
            otp_df = pd.DataFrame(otp_messages)[['otp_code', 'company_name', 'purpose', 'confidence_score', 'raw_message']]
            st.dataframe(otp_df)

    # EMI Messages
    if emi_messages:
        with st.expander(f"💳 Parsed EMI Messages ({len(emi_messages)})", expanded=False):
            st.subheader("EMI Statistics")
            emi_stats = results.get('summary_statistics', {}).get('emi_stats', {})
            st.json(emi_stats)

            st.subheader("Parsed Data")
            emi_df = pd.DataFrame(emi_messages)[['emi_amount', 'emi_due_date', 'bank_name', 'account_number', 'confidence_score', 'raw_message']]
            st.dataframe(emi_df)

    # Challan Messages
    if challan_messages:
        with st.expander(f"🚦 Parsed Traffic Challan Messages ({len(challan_messages)})", expanded=False):
            st.subheader("Challan Statistics")
            challan_stats = results.get('summary_statistics', {}).get('challan_stats', {})
            st.json(challan_stats)

            st.subheader("Parsed Data")
            challan_df = pd.DataFrame(challan_messages)[['challan_number', 'vehicle_number', 'fine_amount', 'challan_status', 'traffic_authority', 'confidence_score', 'raw_message']]
            st.dataframe(challan_df)
            
    # Transportation Messages
    if transport_messages:
        with st.expander(f"✈️ Parsed Transportation Messages ({len(transport_messages)})", expanded=False):
            st.subheader("Transportation Statistics")
            transport_stats = results.get('summary_statistics', {}).get('transportation_stats', {})
            st.json(transport_stats)

            st.subheader("Parsed Data")
            transport_df = pd.DataFrame(transport_messages)[['pnr_number', 'confidence_score', 'raw_message']]
            st.dataframe(transport_df)

    # EPF Messages
    if epf_messages:
        with st.expander(f"💰 Parsed EPF Messages ({len(epf_messages)})", expanded=False):
            st.subheader("EPF Statistics")
            epf_stats = results.get('summary_statistics', {}).get('epf_stats', {})
            st.json(epf_stats)

            st.subheader("Parsed Data")
            epf_df = pd.DataFrame(epf_messages)[['amount_credited', 'available_balance', 'uan_number', 'confidence_score', 'raw_message']]
            st.dataframe(epf_df)

    # E-commerce Messages
    if ecommerce_messages:
        with st.expander(f"📦 Parsed E-commerce & Delivery Messages ({len(ecommerce_messages)})", expanded=False):
            st.subheader("E-commerce Statistics")
            ecommerce_stats = results.get('summary_statistics', {}).get('ecommerce_stats', {})
            st.json(ecommerce_stats)

            st.subheader("Parsed Data")
            ecommerce_df = pd.DataFrame(ecommerce_messages)[['order_id', 'platform', 'order_status', 'amount_to_be_paid', 'item_name', 'delivery_date', 'confidence_score', 'raw_message']]
            st.dataframe(ecommerce_df)

    # --- NEW: Electricity Messages Expander ---
    if electricity_messages:
        with st.expander(f"🔌 Parsed Electricity Bill Messages ({len(electricity_messages)})", expanded=False):
            st.subheader("Electricity Bill Statistics")
            electricity_stats = results.get('summary_statistics', {}).get('electricity_stats', {})
            st.json(electricity_stats)

            st.subheader("Parsed Data")
            electricity_df = pd.DataFrame(electricity_messages)[
                ['bill_amount', 'due_date', 'units_consumed', 'consumer_number', 'service_provider', 'bill_status', 'payment_link', 'confidence_score', 'raw_message']
            ]
            st.dataframe(electricity_df)

    # Rejected Messages
    rejected_messages = results.get('rejected_messages', [])
    if rejected_messages:
        with st.expander(f"⚠️ Rejected Messages ({len(rejected_messages)})", expanded=False):
            st.warning("These messages could not be confidently parsed into any category.")
            rejected_df = pd.DataFrame(rejected_messages)
            st.dataframe(rejected_df)

# --- Interactive Analyzer Section ---
st.markdown("---")
st.header("🔬 Interactive Message Analyzer")
st.markdown("Test the parser with a single message.")

message_input = st.text_area("Enter a message to analyze:")
sender_input = st.text_input("Enter sender name (optional):")
interactive_message_type = st.selectbox(
    "Select Message Type for Analysis", 
    message_type_options, 
    index=0,
    key="interactive_selector"
)

if st.button("Analyze Message", use_container_width=True):
    if message_input:
        with st.spinner("Analyzing..."):
            result = parser.parse_single_message(message_input, sender_input, interactive_message_type)
            
            st.subheader("Analysis Result")
            
            # Display core info
            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("Status", result['status'].title())
            res_col2.metric("Detected Type", result.get('message_type', 'N/A').title())
            res_col3.metric("Confidence Score", f"{result.get('confidence_score', 0)}%")

            # Display detailed parsed data
            if result['status'] == 'parsed':
                st.success("Message parsed successfully!")
                
                # Create a clean dictionary for display
                display_data = result.copy()
                # Remove keys that are not useful for direct display
                keys_to_remove = ['status', 'message_type', 'confidence_score', 'raw_message']
                for key in keys_to_remove:
                    display_data.pop(key, None)
                
                st.json(display_data)

            else:
                st.error("Message could not be parsed.")
                st.write(f"**Reason:** {result.get('reason', 'No specific reason provided.')}")
    else:
        st.warning("Please enter a message to analyze.")