import streamlit as st
import pandas as pd
import json
import io
from typing import Dict, List, Optional
import time
from datetime import datetime
import requests

# Note: Make sure the enhanced parser with the e-commerce module is saved as 'enhanced_parsing.py'
from enhanced_parsing import EnhancedMessageParser

def get_pnr_status(pnr_number):
    """Fetch PNR status from IRCTC API"""
    try:
        url = "https://irctc1.p.rapidapi.com/api/v2/getPNRStatus"
        querystring = {"pnrNumber": pnr_number}
        headers = {
            "x-rapidapi-key": "599097cf20mshf6d2175c1e80216p1b66b0jsn5ce2d24a94c8",
            "x-rapidapi-host": "irctc1.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {"status": True, "data": data.get("data", {}), "raw": data}
        else:
            return {"status": False, "message": f"API Error: {response.status_code}"}

    except requests.exceptions.Timeout:
        return {"status": False, "message": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"status": False, "message": f"Network error: {str(e)}"}
    except Exception as e:
        return {"status": False, "message": f"Unexpected error: {str(e)}"}


def display_pnr_status(pnr_data):
    """Display PNR status with detailed train & passenger info"""

    if not pnr_data:
        st.error("❌ No PNR data available.")
        return

    success = bool(pnr_data.get("status")) or ("data" in pnr_data and pnr_data.get("data"))
    if not success:
        st.error(f"❌ Failed: {pnr_data.get('message', 'Unknown error')}")
        with st.expander("Raw Debug Info"):
            st.json(pnr_data)
        return

    data = pnr_data.get("data", {})

    # ✅ Train Information
    st.subheader("🚆 Train Information")
    c1, c2, c3 = st.columns(3)
    c1.metric("Train Name", data.get("train_name", "N/A"))
    c2.metric("Train No.", data.get("train_number", "N/A"))
    c3.metric("Class", data.get("class", "N/A"))

    c4, c5, c6 = st.columns(3)
    c4.metric("Quota", data.get("quota", "N/A"))
    c5.metric("Journey Date", data.get("journey_date", data.get("date", "N/A")))
    c6.metric("Duration", data.get("journey_duration", "N/A"))

    # ✅ Station Info
    st.subheader("🛤️ Route Information")
    c7, c8 = st.columns(2)
    boarding = data.get("boarding_station", {})
    dest = data.get("reservation_upto", {})
    with c7:
        st.markdown("**Boarding Station**")
        st.write(f"{boarding.get('station_name','N/A')} ({boarding.get('station_code','')})")
        st.write(f"Departure: {boarding.get('departure_time','N/A')} (Day {boarding.get('day_count','-')})")
    with c8:
        st.markdown("**Destination Station**")
        st.write(f"{dest.get('station_name','N/A')} ({dest.get('station_code','')})")
        st.write(f"Arrival: {dest.get('arrival_time','N/A')} (Day {dest.get('day_count','-')})")

    # ✅ Passenger Info
    st.subheader("👥 Passenger Details")
    passengers = data.get("passenger", [])
    if passengers:
        df_pass = pd.DataFrame(passengers)
        # select relevant columns
        show_cols = ["passengerName", "passengerAge", "bookingStatus", "currentStatus", 
                     "currentCoachId", "currentBerthNo", "currentBerthCode"]
        df_show = df_pass[show_cols].rename(columns={
            "passengerName": "Name",
            "passengerAge": "Age",
            "bookingStatus": "Booking Status",
            "currentStatus": "Current Status",
            "currentCoachId": "Coach",
            "currentBerthNo": "Berth No",
            "currentBerthCode": "Berth Code"
        })
        st.dataframe(df_show, use_container_width=True)
    else:
        st.info("No passenger details found.")

    # ✅ Raw JSON Expander
    with st.expander("Raw API JSON"):
        st.json(pnr_data)



def main():
    st.set_page_config(
        page_title="Enhanced Message Parser v13.0 - OTP, EMI, Challan, Transport, EPF & E-commerce",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📦 Enhanced Message Parser v13.0")
    st.markdown("**Advanced parser for OTP, EMI, Challan, Transportation, EPF, and E-commerce messages**")
    st.success("✨ **NEW v13.0**: Added E-commerce and delivery tracking message parsing! 🚚")

    if "parser" not in st.session_state:
        st.session_state.parser = EnhancedMessageParser()

    parser = st.session_state.parser

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

    if "last_single_result" not in st.session_state:
        st.session_state.last_single_result = None
    if "message_text" not in st.session_state:
        st.session_state.message_text = ""

    with st.form("single_form", clear_on_submit=False):
        msg = st.text_area(
            "Message Content",
            value=st.session_state.message_text,
            placeholder="Enter the SMS message text here...",
            height=150
        )
        sender_name = st.text_input("Sender Name (Optional)", placeholder="e.g., Google, IRCTC, Meesho")
        message_type = st.selectbox(
            "Message Type",
            ["auto", "otp", "emi", "challan", "transportation", "epf", "ecommerce"]
        )
        submitted = st.form_submit_button("🔍 Analyze Message")

    if submitted and msg.strip():
        with st.spinner("Analyzing message..."):
            st.session_state.message_text = msg
            st.session_state.last_single_result = parser.parse_single_message(msg, sender_name, message_type)

    result = st.session_state.last_single_result
    if result:
        st.divider()
        st.subheader("📊 Analysis Results")
        confidence = result.get("confidence_score", 0)
        msg_type = result.get("message_type", "Unknown")

        if result.get("status") == "parsed":
            if msg_type == "otp":
                display_otp_results(result, confidence)
            elif msg_type == "emi":
                display_emi_results(result, confidence)
            elif msg_type == "challan":
                display_challan_results(result, confidence)
            elif msg_type == "transportation":
                display_transportation_results(result, confidence)
            elif msg_type == "epf":
                display_epf_results(result, confidence)
            elif msg_type == "ecommerce":
                display_ecommerce_results(result, confidence)
        else:
            st.error(f"❌ Not Classified (Type: {msg_type}, Confidence: {confidence}%)")
            st.warning(f"Reason: {result.get('reason')}")
            with st.expander("Message Preview"):
                st.text(result.get("message_preview"))


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
    elif challan_status == 'court_disposal': # NEW: Handle court disposal status
        status_emoji = "⚖️"
        alert_type = st.error
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
        elif challan_status == 'court_disposal': # NEW: Status description for court disposal
            st.error("⚖️ **Status**: Sent to Court")
            st.error("❗ This challan must be handled through court proceedings.")
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

def display_transportation_results(result, confidence):
    """Display Transportation parsing results - SIMPLIFIED TO PNR ONLY"""
    st.info(f"🚂 **Transportation Message Detected** (Confidence: {confidence}%)")
    
    # SIMPLIFIED: Only show PNR information
    st.markdown("##### 🎫 PNR Information")
    
    pnr_number = result.get('pnr_number')
    
    if pnr_number:
        st.success(f"**PNR Number Found**: {pnr_number}")

        pnr_key = f"pnr_data_{pnr_number}"
        if pnr_key not in st.session_state:
            st.session_state[pnr_key] = None

        # Check PNR button
        if st.button(f"🔍 Check PNR Status: {pnr_number}", key=f"pnr_check_{pnr_number}"):
            with st.spinner(f"Fetching PNR status for {pnr_number}..."):
                st.session_state[pnr_key] = get_pnr_status(pnr_number)

        # Show status if already fetched
        if st.session_state[pnr_key] is not None:
            st.divider()
            st.subheader(f"🚂 PNR Status for {pnr_number}")
            display_pnr_status(st.session_state[pnr_key])

            # Clear button (no rerun needed)
            if st.button(f"🗑️ Clear PNR Status", key=f"pnr_clear_{pnr_number}"):
                st.session_state[pnr_key] = None
    else:
        st.warning("❌ **PNR Number**: Not Found")
    
    # SIMPLIFIED: Only show PNR extraction status
    st.divider()
    st.markdown("##### 📋 Extraction Summary")
    
    if pnr_number:
        st.write("✅ PNR Number Successfully Extracted")
        st.info("💡 **Note**: Transportation parsing is now focused on PNR extraction only. Use the PNR status check above to get detailed journey information.")
    else:
        st.write("❌ PNR Number Not Found")
        st.warning("⚠️ This transportation message does not contain a recognizable PNR number.")
    
    with st.expander("Full Raw Output"):
        st.json(result)

def display_epf_results(result, confidence):
    """Display EPF parsing results"""
    st.success(f"💰 **EPF Message Detected** (Confidence: {confidence}%)")

    col1, col2 = st.columns(2)
    amount_credited = result.get('amount_credited')
    col1.metric("Amount Credited", f"₹{amount_credited}" if amount_credited else "Not Mentioned")
    col2.metric("UAN Number", result.get('uan_number') or "Not Found")

    col3, col4 = st.columns(2)
    available_balance = result.get('available_balance')
    col3.metric("Available Balance", f"₹{available_balance}" if available_balance else "Not Mentioned")

    account = result.get('account_number')
    masked_account = f"****{account[-4:]}" if account and len(account) > 4 else account
    col4.metric("Account Number", masked_account or "Not Found")

    st.divider()
    st.markdown("##### 📋 Extracted Information Summary")
    
    info_completeness = []
    info_completeness.append("✅ Amount" if result.get('amount_credited') else "❌ Amount")
    info_completeness.append("✅ UAN" if result.get('uan_number') else "❌ UAN")
    info_completeness.append("✅ Balance" if result.get('available_balance') else "❌ Balance")
    info_completeness.append("✅ Account" if result.get('account_number') else "❌ Account")
    st.write(" | ".join(info_completeness))
    
    if "auto claim" in result.get('raw_message', '').lower():
        st.info("ℹ️ **EPF Transfer Notification**: This message relates to the transfer of EPF accumulations.")
    elif "contribution" in result.get('raw_message', '').lower():
        st.success("✅ **EPF Contribution Received**: This message confirms a received contribution.")
    
    with st.expander("Full Raw Output"):
        st.json(result)

# UPDATED: Display function for E-commerce results
def display_ecommerce_results(result, confidence):
    """Display E-commerce and Delivery parsing results"""
    st.success(f"📦 **E-commerce & Delivery Message Detected** (Confidence: {confidence}%)")

    # Main order information - Changed to a 2x3 grid
    col1, col2, col3 = st.columns(3)

    order_id = result.get('order_id')
    col1.metric("Order/Tracking ID", order_id or "Not Found")

    platform = result.get('platform')
    col2.metric("Platform", platform or "Not Identified")

    order_status = result.get('order_status', 'update').replace('_', ' ').title()
    col3.metric("Order Status", order_status)

    col4, col5, col6 = st.columns(3)

    item_name = result.get('item_name')
    col4.metric("Item Name", item_name or "Not Found")

    delivery_date = result.get('delivery_date')
    col5.metric("Delivery Date", delivery_date or "Not Specified")

    amount_to_be_paid = result.get('amount_to_be_paid')
    col6.metric("Amount to Pay (COD)", f"₹{amount_to_be_paid}" if amount_to_be_paid else "N/A")

    st.divider()

    # Information completeness summary - UPDATED
    st.markdown("##### 📋 Extracted Information Summary")

    info_completeness = []
    info_completeness.append("✅ Order ID" if result.get('order_id') else "❌ Order ID")
    info_completeness.append("✅ Platform" if result.get('platform') else "❌ Platform")
    info_completeness.append("✅ Status" if result.get('order_status') != 'update' else "⚪️ Status")
    info_completeness.append("✅ Item Name" if result.get('item_name') else "❌ Item Name")
    info_completeness.append("✅ Delivery Date" if result.get('delivery_date') else "❌ Delivery Date")
    info_completeness.append("✅ COD Amount" if result.get('amount_to_be_paid') else "❌ COD Amount")
    st.write(" | ".join(info_completeness))

    with st.expander("Full Raw Output"):
        st.json(result)


def csv_processing_interface(parser):
    st.header("📊 CSV File Processing")

    if "csv_store" not in st.session_state:
        st.session_state.csv_store = None

    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)
            st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")

            if "message" not in df.columns:
                st.error("CSV must contain a 'message' column.")
                return
            if "sender_name" not in df.columns:
                df["sender_name"] = ""

            st.dataframe(df.head())

            with st.form("csv_form", clear_on_submit=False):
                col1, col2 = st.columns(2)
                with col1:
                    message_type = st.selectbox("Message Type", ["auto", "otp", "emi", "challan", "transportation", "epf", "ecommerce"])
                with col2:
                    confidence_threshold = st.slider("Confidence Threshold", 0, 100, 40)
                csv_submitted = st.form_submit_button("🚀 Process Messages")

            if csv_submitted:
                progress_bar = st.progress(0)
                status_text = st.empty()
                results = []
                total_rows = len(df)
                start_time = time.time()

                for i, row in df.iterrows():
                    results.append(parser.parse_single_message(row["message"], row.get("sender_name", ""), message_type))
                    progress = (i + 1) / total_rows
                    progress_bar.progress(progress)
                    if (i + 1) % 100 == 0 or i == total_rows - 1:
                        elapsed = time.time() - start_time
                        rate = (i + 1) / elapsed if elapsed > 0 else 0
                        status_text.text(f"Processed: {i+1:,}/{total_rows:,} ({progress*100:.1f}%) | {rate:.0f} msgs/sec")

                results_df = pd.DataFrame(results)
                parsed_df = results_df[
                    (results_df["status"] == "parsed") &
                    (results_df["confidence_score"] >= confidence_threshold)
                ]
                rejected_df = results_df[
                    (results_df["status"] == "rejected") |
                    (results_df["confidence_score"] < confidence_threshold)
                ]

                st.session_state.csv_store = {
                    "parsed_df": parsed_df,
                    "rejected_df": rejected_df,
                    "total_rows": total_rows
                }

        except Exception as e:
            st.error(f"Error: {e}")

    # always render results if present
    store = st.session_state.get("csv_store")
    if store:
        parsed_df = store["parsed_df"]
        rejected_df = store["rejected_df"]
        total_rows = store["total_rows"]

        st.subheader("📈 Processing Summary")
        st.metric("Total Parsed", f"{len(parsed_df):,}")
        st.metric("Rejected", f"{len(rejected_df):,}")
        st.metric("Overall Detection Rate", f"{(len(parsed_df)/total_rows*100):.2f}%")

        # show sample rejected
        if len(rejected_df) > 0:
            with st.expander(f"📋 Sample Rejected Messages ({len(rejected_df):,})"):
                st.dataframe(rejected_df.head(10))


def main_app():
    main()


if __name__ == "__main__":
    main_app()










































    ## Old Code

#     import streamlit as st
# import pandas as pd
# import json
# import io
# from typing import Dict, List, Optional
# import time
# from datetime import datetime
# import requests

# # Note: Make sure the enhanced parser is saved as 'enhanced_parsing.py'
# from enhanced_parsing import EnhancedMessageParser

# def get_pnr_status(pnr_number):
#     """Fetch PNR status from IRCTC API"""
#     try:
#         url = "https://irctc1.p.rapidapi.com/api/v2/getPNRStatus"
#         querystring = {"pnrNumber": pnr_number}
#         headers = {
#             "x-rapidapi-key": "599097cf20mshf6d2175c1e80216p1b66b0jsn5ce2d24a94c8",
#             "x-rapidapi-host": "irctc1.p.rapidapi.com"
#         }

#         response = requests.get(url, headers=headers, params=querystring, timeout=10)

#         if response.status_code == 200:
#             data = response.json()
#             return {"status": True, "data": data.get("data", {}), "raw": data}
#         else:
#             return {"status": False, "message": f"API Error: {response.status_code}"}

#     except requests.exceptions.Timeout:
#         return {"status": False, "message": "Request timed out. Please try again."}
#     except requests.exceptions.RequestException as e:
#         return {"status": False, "message": f"Network error: {str(e)}"}
#     except Exception as e:
#         return {"status": False, "message": f"Unexpected error: {str(e)}"}


# def display_pnr_status(pnr_data):
#     """Display PNR status with detailed train & passenger info"""

#     if not pnr_data:
#         st.error("❌ No PNR data available.")
#         return

#     success = bool(pnr_data.get("status")) or ("data" in pnr_data and pnr_data.get("data"))
#     if not success:
#         st.error(f"❌ Failed: {pnr_data.get('message', 'Unknown error')}")
#         with st.expander("Raw Debug Info"):
#             st.json(pnr_data)
#         return

#     data = pnr_data.get("data", {})

#     # ✅ Train Information
#     st.subheader("🚆 Train Information")
#     c1, c2, c3 = st.columns(3)
#     c1.metric("Train Name", data.get("train_name", "N/A"))
#     c2.metric("Train No.", data.get("train_number", "N/A"))
#     c3.metric("Class", data.get("class", "N/A"))

#     c4, c5, c6 = st.columns(3)
#     c4.metric("Quota", data.get("quota", "N/A"))
#     c5.metric("Journey Date", data.get("journey_date", data.get("date", "N/A")))
#     c6.metric("Duration", data.get("journey_duration", "N/A"))

#     # ✅ Station Info
#     st.subheader("🛤️ Route Information")
#     c7, c8 = st.columns(2)
#     boarding = data.get("boarding_station", {})
#     dest = data.get("reservation_upto", {})
#     with c7:
#         st.markdown("**Boarding Station**")
#         st.write(f"{boarding.get('station_name','N/A')} ({boarding.get('station_code','')})")
#         st.write(f"Departure: {boarding.get('departure_time','N/A')} (Day {boarding.get('day_count','-')})")
#     with c8:
#         st.markdown("**Destination Station**")
#         st.write(f"{dest.get('station_name','N/A')} ({dest.get('station_code','')})")
#         st.write(f"Arrival: {dest.get('arrival_time','N/A')} (Day {dest.get('day_count','-')})")

#     # ✅ Passenger Info
#     st.subheader("👥 Passenger Details")
#     passengers = data.get("passenger", [])
#     if passengers:
#         df_pass = pd.DataFrame(passengers)
#         # select relevant columns
#         show_cols = ["passengerName", "passengerAge", "bookingStatus", "currentStatus", 
#                      "currentCoachId", "currentBerthNo", "currentBerthCode"]
#         df_show = df_pass[show_cols].rename(columns={
#             "passengerName": "Name",
#             "passengerAge": "Age",
#             "bookingStatus": "Booking Status",
#             "currentStatus": "Current Status",
#             "currentCoachId": "Coach",
#             "currentBerthNo": "Berth No",
#             "currentBerthCode": "Berth Code"
#         })
#         st.dataframe(df_show, use_container_width=True)
#     else:
#         st.info("No passenger details found.")

#     # ✅ Raw JSON Expander
#     with st.expander("Raw API JSON"):
#         st.json(pnr_data)



# def main():
#     st.set_page_config(
#         page_title="Enhanced Message Parser v12.0 - OTP, EMI, Challan, Transport & EPF",
#         page_icon="💸",
#         layout="wide",
#         initial_sidebar_state="expanded"
#     )

#     st.title("💸 Enhanced Message Parser v12.0")
#     st.markdown("**Advanced parser for OTP, EMI, Challan, Transportation, and EPF messages**")
#     st.success("✨ **NEW v12.0**: Transportation parsing simplified to PNR extraction only! 🚂")

#     if "parser" not in st.session_state:
#         st.session_state.parser = EnhancedMessageParser()

#     parser = st.session_state.parser

#     st.sidebar.title("Navigation")
#     mode = st.sidebar.radio(
#         "Choose analysis mode:",
#         ["Single Message Analysis", "CSV File Processing"]
#     )

#     if mode == "Single Message Analysis":
#         single_message_interface(parser)
#     elif mode == "CSV File Processing":
#         csv_processing_interface(parser)


# def single_message_interface(parser):
#     st.header("📱 Single Message Analysis")

#     if "last_single_result" not in st.session_state:
#         st.session_state.last_single_result = None
#     if "message_text" not in st.session_state:
#         st.session_state.message_text = ""

#     with st.form("single_form", clear_on_submit=False):
#         msg = st.text_area(
#             "Message Content",
#             value=st.session_state.message_text,
#             placeholder="Enter the SMS message text here...",
#             height=150
#         )
#         sender_name = st.text_input("Sender Name (Optional)", placeholder="e.g., Google, IRCTC")
#         message_type = st.selectbox(
#             "Message Type",
#             ["auto", "otp", "emi", "challan", "transportation", "epf"]
#         )
#         submitted = st.form_submit_button("🔍 Analyze Message")

#     if submitted and msg.strip():
#         with st.spinner("Analyzing message..."):
#             st.session_state.message_text = msg
#             st.session_state.last_single_result = parser.parse_single_message(msg, sender_name, message_type)

#     result = st.session_state.last_single_result
#     if result:
#         st.divider()
#         st.subheader("📊 Analysis Results")
#         confidence = result.get("confidence_score", 0)
#         msg_type = result.get("message_type", "Unknown")

#         if result.get("status") == "parsed":
#             if msg_type == "otp":
#                 display_otp_results(result, confidence)
#             elif msg_type == "emi":
#                 display_emi_results(result, confidence)
#             elif msg_type == "challan":
#                 display_challan_results(result, confidence)
#             elif msg_type == "transportation":
#                 display_transportation_results(result, confidence)
#             elif msg_type == "epf":
#                 display_epf_results(result, confidence)
#         else:
#             st.error(f"❌ Not Classified (Type: {msg_type}, Confidence: {confidence}%)")
#             st.warning(f"Reason: {result.get('reason')}")
#             with st.expander("Message Preview"):
#                 st.text(result.get("message_preview"))


# def display_otp_results(result, confidence):
#     """Display OTP parsing results"""
#     st.success(f"✅ **OTP Message Detected** (Confidence: {confidence}%)")
    
#     col1, col2 = st.columns(2)
#     col1.metric("Extracted OTP", result.get('otp_code', "N/A"))
#     col2.metric("Company", result.get('company_name', "Unknown"))
    
#     st.divider()
    
#     st.markdown("##### ℹ️ Additional Details")
#     col3, col4 = st.columns(2)
    
#     purpose = result.get('purpose') or "General"
#     col3.metric("Purpose", purpose)
    
#     expiry_info = result.get('expiry_info')
#     if expiry_info:
#         try:
#             duration = int(expiry_info.get('duration', 0))
#             unit = expiry_info.get('unit', 'min')
#             plural_s = 's' if duration > 1 else ''
#             expiry_text = f"{duration} {unit}{plural_s}"
#         except (ValueError, TypeError):
#             expiry_text = "Not Specified"
#     else:
#         expiry_text = "Not Specified"
#     col4.metric("Validity", expiry_text)
    
#     security_warnings = result.get('security_warnings')
#     if security_warnings:
#         st.warning(f"**Security Advice**: {', '.join(security_warnings).title()}")
    
#     with st.expander("Full Raw Output"):
#         st.json(result)

# def display_emi_results(result, confidence):
#     """Display EMI parsing results"""
#     st.success(f"✅ **EMI Message Detected** (Confidence: {confidence}%)")
    
#     # Main EMI information
#     col1, col2, col3, col4 = st.columns(4)
    
#     emi_amount = result.get('emi_amount')
#     if emi_amount:
#         col1.metric("EMI Amount", f"₹{emi_amount}")
#     else:
#         col1.metric("EMI Amount", "Not Found")
    
#     due_date = result.get('emi_due_date')
#     if due_date:
#         col2.metric("Due Date", due_date)
#     else:
#         col2.metric("Due Date", "Not Specified")
    
#     bank_name = result.get('bank_name')
#     if bank_name:
#         col3.metric("Bank/Lender", bank_name)
#     else:
#         col3.metric("Bank/Lender", "Not Identified")
    
#     account_number = result.get('account_number')
#     if account_number:
#         # Mask account number for security
#         masked_account = f"****{account_number[-4:]}" if len(account_number) > 4 else account_number
#         col4.metric("Account", masked_account)
#     else:
#         col4.metric("Account", "Not Found")
    
#     # Additional info
#     st.divider()
#     st.markdown("##### 📋 Extracted Information Summary")
    
#     info_completeness = []
#     if emi_amount:
#         info_completeness.append("✅ EMI Amount")
#     else:
#         info_completeness.append("❌ EMI Amount")
        
#     if due_date:
#         info_completeness.append("✅ Due Date")
#     else:
#         info_completeness.append("❌ Due Date")
        
#     if bank_name:
#         info_completeness.append("✅ Bank/Lender")
#     else:
#         info_completeness.append("❌ Bank/Lender")
        
#     if account_number:
#         info_completeness.append("✅ Account Number")
#     else:
#         info_completeness.append("❌ Account Number")
    
#     st.write(" | ".join(info_completeness))
    
#     with st.expander("Full Raw Output"):
#         st.json(result)

# def display_challan_results(result, confidence):
#     """Display Traffic Challan parsing results - Enhanced with new status types"""
#     challan_status = result.get('challan_status', 'unknown')
    
#     # Enhanced status colors and alerts
#     if challan_status == 'paid':
#         status_emoji = "✅"
#         alert_type = st.success
#     elif challan_status == 'pending':
#         status_emoji = "🚨"
#         alert_type = st.warning
#     elif challan_status == 'court_disposal': # NEW: Handle court disposal status
#         status_emoji = "⚖️"
#         alert_type = st.error
#     else:  # issued
#         status_emoji = "📋"
#         alert_type = st.info
    
#     alert_type(f"{status_emoji} **Traffic Challan Detected** (Confidence: {confidence}%)")
    
#     # Main challan information
#     col1, col2, col3, col4 = st.columns(4)
    
#     challan_number = result.get('challan_number')
#     if challan_number:
#         col1.metric("Challan Number", challan_number)
#     else:
#         col1.metric("Challan Number", "Not Found")
    
#     vehicle_number = result.get('vehicle_number')
#     if vehicle_number:
#         col2.metric("Vehicle Number", vehicle_number)
#     else:
#         col2.metric("Vehicle Number", "Not Found")
    
#     fine_amount = result.get('fine_amount')
#     if fine_amount:
#         col3.metric("Fine Amount", f"₹{fine_amount}")
#     else:
#         col3.metric("Fine Amount", "Not Specified")
    
#     authority = result.get('traffic_authority')
#     if authority:
#         col4.metric("Authority", authority)
#     else:
#         col4.metric("Authority", "Not Identified")
    
#     # Enhanced status and payment information
#     st.divider()
    
#     col5, col6 = st.columns(2)
    
#     with col5:
#         st.markdown("##### 🔗 Payment Information")
#         payment_link = result.get('payment_link')
#         if payment_link:
#             st.success("Payment Link Available")
#             st.markdown(f"**Link**: {payment_link}")
#             if st.button("🌐 Open Payment Portal"):
#                 st.markdown(f"[Open in new tab]({payment_link})")
#         else:
#             st.info("No payment link found in message")
    
#     with col6:
#         st.markdown("##### 📊 Challan Status")
        
#         # Enhanced status descriptions
#         if challan_status == 'paid':
#             st.success("✅ **Status**: Payment Confirmed")
#             st.info("💡 This is a payment confirmation or receipt message")
#         elif challan_status == 'pending':
#             st.warning("🚨 **Status**: Payment Pending")
#             st.warning("⚠️ This challan requires immediate payment")
#         elif challan_status == 'issued':
#             st.info("📋 **Status**: Newly Issued")
#             st.info("ℹ️ This is a new challan notification or payment initiation")
#         elif challan_status == 'court_disposal': # NEW: Status description for court disposal
#             st.error("⚖️ **Status**: Sent to Court")
#             st.error("❗ This challan must be handled through court proceedings.")
#         else:
#             st.info(f"📄 **Status**: {challan_status.title()}")
    
#     # Information completeness summary
#     st.divider()
#     st.markdown("##### 📋 Extracted Information Summary")
    
#     info_completeness = []
#     if challan_number:
#         info_completeness.append("✅ Challan Number")
#     else:
#         info_completeness.append("❌ Challan Number")
        
#     if vehicle_number:
#         info_completeness.append("✅ Vehicle Number")
#     else:
#         info_completeness.append("❌ Vehicle Number")
        
#     if fine_amount:
#         info_completeness.append("✅ Fine Amount")
#     else:
#         info_completeness.append("❌ Fine Amount")
        
#     if payment_link:
#         info_completeness.append("✅ Payment Link")
#     else:
#         info_completeness.append("❌ Payment Link")
    
#     st.write(" | ".join(info_completeness))
    
#     # NEW: Enhanced challan type detection
#     if challan_status == 'paid':
#         st.success("🎉 **Payment Confirmation**: This message confirms a successful challan payment")
#     elif "reference" in result.get('raw_message', '').lower():
#         st.info("🔑 **Payment Reference**: This appears to be a payment reference or transaction ID")
    
#     with st.expander("Full Raw Output"):
#         st.json(result)

# def display_transportation_results(result, confidence):
#     """Display Transportation parsing results - SIMPLIFIED TO PNR ONLY"""
#     st.info(f"🚂 **Transportation Message Detected** (Confidence: {confidence}%)")
    
#     # SIMPLIFIED: Only show PNR information
#     st.markdown("##### 🎫 PNR Information")
    
#     pnr_number = result.get('pnr_number')
    
#     if pnr_number:
#         st.success(f"**PNR Number Found**: {pnr_number}")

#         pnr_key = f"pnr_data_{pnr_number}"
#         if pnr_key not in st.session_state:
#             st.session_state[pnr_key] = None

#         # Check PNR button
#         if st.button(f"🔍 Check PNR Status: {pnr_number}", key=f"pnr_check_{pnr_number}"):
#             with st.spinner(f"Fetching PNR status for {pnr_number}..."):
#                 st.session_state[pnr_key] = get_pnr_status(pnr_number)

#         # Show status if already fetched
#         if st.session_state[pnr_key] is not None:
#             st.divider()
#             st.subheader(f"🚂 PNR Status for {pnr_number}")
#             display_pnr_status(st.session_state[pnr_key])

#             # Clear button (no rerun needed)
#             if st.button(f"🗑️ Clear PNR Status", key=f"pnr_clear_{pnr_number}"):
#                 st.session_state[pnr_key] = None
#     else:
#         st.warning("❌ **PNR Number**: Not Found")
    
#     # SIMPLIFIED: Only show PNR extraction status
#     st.divider()
#     st.markdown("##### 📋 Extraction Summary")
    
#     if pnr_number:
#         st.write("✅ PNR Number Successfully Extracted")
#         st.info("💡 **Note**: Transportation parsing is now focused on PNR extraction only. Use the PNR status check above to get detailed journey information.")
#     else:
#         st.write("❌ PNR Number Not Found")
#         st.warning("⚠️ This transportation message does not contain a recognizable PNR number.")
    
#     with st.expander("Full Raw Output"):
#         st.json(result)

# # NEW: Display function for EPF results
# def display_epf_results(result, confidence):
#     """Display EPF parsing results"""
#     st.success(f"💰 **EPF Message Detected** (Confidence: {confidence}%)")

#     col1, col2 = st.columns(2)
#     amount_credited = result.get('amount_credited')
#     col1.metric("Amount Credited", f"₹{amount_credited}" if amount_credited else "Not Mentioned")
#     col2.metric("UAN Number", result.get('uan_number') or "Not Found")

#     col3, col4 = st.columns(2)
#     available_balance = result.get('available_balance')
#     col3.metric("Available Balance", f"₹{available_balance}" if available_balance else "Not Mentioned")

#     account = result.get('account_number')
#     masked_account = f"****{account[-4:]}" if account and len(account) > 4 else account
#     col4.metric("Account Number", masked_account or "Not Found")

#     st.divider()
#     st.markdown("##### 📋 Extracted Information Summary")
    
#     info_completeness = []
#     info_completeness.append("✅ Amount" if result.get('amount_credited') else "❌ Amount")
#     info_completeness.append("✅ UAN" if result.get('uan_number') else "❌ UAN")
#     info_completeness.append("✅ Balance" if result.get('available_balance') else "❌ Balance")
#     info_completeness.append("✅ Account" if result.get('account_number') else "❌ Account")
#     st.write(" | ".join(info_completeness))
    
#     if "auto claim" in result.get('raw_message', '').lower():
#         st.info("ℹ️ **EPF Transfer Notification**: This message relates to the transfer of EPF accumulations.")
#     elif "contribution" in result.get('raw_message', '').lower():
#         st.success("✅ **EPF Contribution Received**: This message confirms a received contribution.")
    
#     with st.expander("Full Raw Output"):
#         st.json(result)


# def csv_processing_interface(parser):
#     st.header("📊 CSV File Processing")

#     if "csv_store" not in st.session_state:
#         st.session_state.csv_store = None

#     uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
#     if uploaded_file:
#         try:
#             df = pd.read_csv(uploaded_file, dtype=str)
#             st.success(f"✅ File uploaded successfully! Found {len(df):,} rows")

#             if "message" not in df.columns:
#                 st.error("CSV must contain a 'message' column.")
#                 return
#             if "sender_name" not in df.columns:
#                 df["sender_name"] = ""

#             st.dataframe(df.head())

#             with st.form("csv_form", clear_on_submit=False):
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     message_type = st.selectbox("Message Type", ["auto", "otp", "emi", "challan", "transportation", "epf"])
#                 with col2:
#                     confidence_threshold = st.slider("Confidence Threshold", 0, 100, 40)
#                 csv_submitted = st.form_submit_button("🚀 Process Messages")

#             if csv_submitted:
#                 progress_bar = st.progress(0)
#                 status_text = st.empty()
#                 results = []
#                 total_rows = len(df)
#                 start_time = time.time()

#                 for i, row in df.iterrows():
#                     results.append(parser.parse_single_message(row["message"], row.get("sender_name", ""), message_type))
#                     progress = (i + 1) / total_rows
#                     progress_bar.progress(progress)
#                     if (i + 1) % 100 == 0 or i == total_rows - 1:
#                         elapsed = time.time() - start_time
#                         rate = (i + 1) / elapsed if elapsed > 0 else 0
#                         status_text.text(f"Processed: {i+1:,}/{total_rows:,} ({progress*100:.1f}%) | {rate:.0f} msgs/sec")

#                 results_df = pd.DataFrame(results)
#                 parsed_df = results_df[
#                     (results_df["status"] == "parsed") &
#                     (results_df["confidence_score"] >= confidence_threshold)
#                 ]
#                 rejected_df = results_df[
#                     (results_df["status"] == "rejected") |
#                     (results_df["confidence_score"] < confidence_threshold)
#                 ]

#                 st.session_state.csv_store = {
#                     "parsed_df": parsed_df,
#                     "rejected_df": rejected_df,
#                     "total_rows": total_rows
#                 }

#         except Exception as e:
#             st.error(f"Error: {e}")

#     # always render results if present
#     store = st.session_state.get("csv_store")
#     if store:
#         parsed_df = store["parsed_df"]
#         rejected_df = store["rejected_df"]
#         total_rows = store["total_rows"]

#         st.subheader("📈 Processing Summary")
#         st.metric("Total Parsed", f"{len(parsed_df):,}")
#         st.metric("Rejected", f"{len(rejected_df):,}")
#         st.metric("Overall Detection Rate", f"{(len(parsed_df)/total_rows*100):.2f}%")

#         # show sample rejected
#         if len(rejected_df) > 0:
#             with st.expander(f"📋 Sample Rejected Messages ({len(rejected_df):,})"):
#                 st.dataframe(rejected_df.head(10))


# def main_app():
#     main()


# if __name__ == "__main__":
#     main_app()