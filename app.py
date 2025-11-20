import streamlit as st
import json
import pandas as pd
import tempfile
import os
import requests
from ai_engine import analyze_document_with_gemini

# --- Page Config ---
st.set_page_config(page_title="FinSight Lite", layout="wide")

st.title("🤖 FinSight Lite: AI Annual Report Analyzer")
st.markdown("Using **Gemini 1.5 Flash** for $0 cost extraction.")

# --- Helper Function: Save Uploaded File to Temp ---
def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

# --- Helper Function: Download PDF from URL ---
def download_pdf_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # Mimic a browser to avoid 403 errors
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status() # Raise error for bad status codes
        
        # Verify content type is PDF
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            st.error("⚠️ The URL provided does not point to a PDF file.")
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name
    except Exception as e:
        st.error(f"❌ Failed to download PDF: {e}")
        return None

# --- Main Interface ---
# Create tabs for the two input methods
tab1, tab2 = st.tabs(["📂 Upload PDF", "🔗 Paste Report URL"])

processing_path = None
file_name = None

# --- TAB 1: File Upload ---
with tab1:
    uploaded_file = st.file_uploader("Upload Annual Report (PDF)", type="pdf")
    if uploaded_file:
        processing_path = save_uploaded_file(uploaded_file)
        file_name = uploaded_file.name

# --- TAB 2: URL Input ---
with tab2:
    url_input = st.text_input("Paste the direct URL to a PDF Report:", placeholder="https://example.com/2024-annual-report.pdf")
    if url_input:
        if st.button("Fetch PDF"):
            with st.spinner("Downloading Document..."):
                downloaded_path = download_pdf_from_url(url_input)
                if downloaded_path:
                    processing_path = downloaded_path
                    file_name = "url_document.pdf"
                    st.success("✅ PDF Downloaded Successfully!")

# --- Analysis Section ---
if processing_path:
    st.divider()
    col1, col2 = st.columns([1, 1])

    with col1:
        st.info(f"📄 Processing: **{file_name}**")
        # Previewing specific pages involves extra libs like pdf2image, 
        # keeping it simple here with just a status indicator.
        
    with col2:
        st.subheader("📊 Financial Data Extraction")
        if st.button("Analyze Report", type="primary"):
            with st.spinner("🤖 AI is reading and extracting data..."):
                try:
                    # Call the AI Engine
                    raw_json = analyze_document_with_gemini(processing_path)
                    
                    # Parse JSON
                    data = json.loads(raw_json)
                    
                    # 1. Display Interactive Editor
                    st.caption("Review and Edit Extracted Data:")
                    df = pd.DataFrame([data]).T.reset_index()
                    df.columns = ["Metric", "Value"]
                    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                    
                    st.success("Analysis Complete!")
                    
                    # 2. Download Button
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "⬇️ Download Data as CSV",
                        csv,
                        "financial_data.csv",
                        "text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"Error during analysis: {e}")
                finally:
                    # Cleanup: Remove the temp file to save space
                    if os.path.exists(processing_path):
                        os.remove(processing_path)
