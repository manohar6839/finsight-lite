import streamlit as st
import json
import pandas as pd
import tempfile
import os
import requests
from pypdf import PdfReader, PdfWriter
from ai_engine import analyze_document_with_gemini

# --- Page Config ---
st.set_page_config(page_title="FinSight Lite", layout="wide")

# --- SIDEBAR: Global Settings (Always Visible) ---
with st.sidebar:
    st.title("⚙️ Analysis Settings")
    st.info("Define these settings *before* or *after* uploading.")
    
    # 1. Page Selection
    st.subheader("1. Page Selection")
    page_selection = st.text_input(
        "Enter Page Numbers:",
        placeholder="e.g., 1, 3-5, 10",
        help="Leave empty to analyze the whole PDF. Use ranges like 3-5."
    )
    if page_selection:
        st.success(f"✅ Sure, Focus Mode: Will check Page {page_selection}")
    else:
        st.markdown("*Analyzing Full Document*")

    st.divider()
    
    # 2. API Diagnostics (For your 404 Error)
    with st.expander("🔧 Troubleshooting", expanded=False):
        st.markdown("If you get a 404 error, check which models are available to your API Key:")
        if st.button("List My Models"):
            try:
                models = get_available_models()
                st.write(models)
            except Exception as e:
                st.error(f"Error: {e}")

# --- Helper Functions ---
def parse_page_selection(selection_str, max_pages):
    if not selection_str or not selection_str.strip():
        return None
    selected_pages = set()
    try:
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                selected_pages.update(range(start - 1, end))
            else:
                selected_pages.add(int(part) - 1)
    except ValueError:
        st.error("⚠️ Invalid page format. Use '1-3, 5' format.")
        return None
    return sorted([p for p in selected_pages if 0 <= p < max_pages])

def extract_pages_from_pdf(input_path, page_indices):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
        writer.write(tmp_out)
        return tmp_out.name

def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

def download_pdf_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        if 'application/pdf' not in response.headers.get('Content-Type', ''):
            st.error("⚠️ URL is not a PDF.")
            return None
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name
    except Exception as e:
        st.error(f"❌ Download failed: {e}")
        return None

# --- Main Content ---
st.title("🤖 FinSight Lite")
st.markdown("Analyze Annual Reports using **Gemini 1.5 Flash**.")

tab1, tab2 = st.tabs(["📂 Upload PDF", "🔗 Paste URL"])
raw_pdf_path = None
file_name = None

with tab1:
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file:
        raw_pdf_path = save_uploaded_file(uploaded_file)
        file_name = uploaded_file.name

with tab2:
    url_input = st.text_input("Enter PDF URL")
    if url_input and st.button("Fetch PDF"):
        with st.spinner("Downloading..."):
            path = download_pdf_from_url(url_input)
            if path:
                raw_pdf_path = path
                file_name = "url_document.pdf"
                st.success("Downloaded!")

if raw_pdf_path:
    st.divider()
    
    # Get Page Count
    try:
        reader = PdfReader(raw_pdf_path)
        total_pages = len(reader.pages)
    except:
        total_pages = 0
        
    st.write(f"📄 **Loaded:** {file_name} ({total_pages} pages)")

    # Validation Logic for Page Selection
    selected_indices = None
    if page_selection:
        selected_indices = parse_page_selection(page_selection, total_pages)
        if selected_indices:
            st.info(f"⚡ Analyzing **{len(selected_indices)}** specific pages out of {total_pages}.")
        else:
            st.warning("⚠️ Page range invalid or out of bounds. Using full document.")

    if st.button("🚀 Analyze Report", type="primary"):
        with st.spinner("Processing..."):
            try:
                final_path = raw_pdf_path
                # Slice if needed
                if selected_indices:
                    final_path = extract_pages_from_pdf(raw_pdf_path, selected_indices)
                
                # CALL AI
                raw_json = analyze_document_with_gemini(final_path)
                data = json.loads(raw_json)
                
                # Display
                st.subheader("Results")
                df = pd.DataFrame([data]).T.reset_index()
                df.columns = ["Metric", "Value"]
                st.data_editor(df, use_container_width=True)
                
                # Cleanup
                if selected_indices and final_path != raw_pdf_path:
                    os.remove(final_path)
                    
            except Exception as e:
                st.error(f"Analysis Failed: {e}")
