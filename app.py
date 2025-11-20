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

st.title("🤖 FinSight Lite: AI Annual Report Analyzer")
st.markdown("Using **Gemini 1.5 Flash** | Optimize costs by selecting specific pages.")

# --- Helper Functions (Same as before) ---
def parse_page_selection(selection_str, max_pages):
    if not selection_str.strip():
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
            st.error("⚠️ The URL provided does not point to a PDF file.")
            return None
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name
    except Exception as e:
        st.error(f"❌ Failed to download PDF: {e}")
        return None

# --- UI Step 1: Input Source ---
st.header("1. Select Document")
tab1, tab2 = st.tabs(["📂 Upload PDF", "🔗 Paste Report URL"])

raw_pdf_path = None
file_name = None

with tab1:
    uploaded_file = st.file_uploader("Upload Annual Report", type="pdf")
    if uploaded_file:
        raw_pdf_path = save_uploaded_file(uploaded_file)
        file_name = uploaded_file.name

with tab2:
    url_input = st.text_input("Paste Report URL:", placeholder="https://example.com/report.pdf")
    if url_input and st.button("Fetch PDF"):
        with st.spinner("Downloading..."):
            path = download_pdf_from_url(url_input)
            if path:
                raw_pdf_path = path
                file_name = "url_document.pdf"
                st.success("✅ Downloaded!")

# --- UI Step 2: Page Selection (Only shows after file is loaded) ---
if raw_pdf_path:
    st.divider()
    st.header("2. Select Pages to Analyze")
    
    # Get Page Count
    try:
        reader = PdfReader(raw_pdf_path)
        total_pages = len(reader.pages)
        st.info(f"📄 **Document Loaded:** {file_name} — Total Pages: **{total_pages}**")
    except Exception:
        st.error("Error reading PDF structure.")
        total_pages = 0

    # --- DISTINCT INPUT SECTION ---
    col_sel, col_info = st.columns([2, 1])
    
    with col_sel:
        page_selection = st.text_input(
            "Enter Page Numbers (Recommended):", 
            placeholder="e.g., 1, 3-5, 10",
            help="Extracting only specific pages makes the AI faster and more accurate."
        )
        
    with col_info:
        # Visual Feedback
        if page_selection:
            st.success("✅ Specific pages selected")
        else:
            st.warning("⚠️ Analyzing entire document (Slower)")

    st.divider()
    
    # --- UI Step 3: Execution ---
    st.header("3. Extraction")
    
    if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
        
        final_pdf_path = raw_pdf_path
        selected_indices = None
        
        # Logic to handle page slicing
        if page_selection:
            selected_indices = parse_page_selection(page_selection, total_pages)
            if selected_indices:
                with st.spinner(f"Slicing PDF to keep only {len(selected_indices)} pages..."):
                    final_pdf_path = extract_pages_from_pdf(raw_pdf_path, selected_indices)
            else:
                st.warning("Invalid page range, using full document.")

        # Run Analysis
        with st.spinner("🤖 AI is reading the document..."):
            try:
                raw_json = analyze_document_with_gemini(final_pdf_path)
                data = json.loads(raw_json)
                
                st.subheader("📊 Extracted Data")
                df = pd.DataFrame([data]).T.reset_index()
                df.columns = ["Metric", "Value"]
                edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                
                # Download
                csv = edited_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download Data as CSV",
                    csv,
                    "financial_data.csv",
                    "text/csv"
                )

                # Cleanup sliced file
                if selected_indices and final_pdf_path != raw_pdf_path:
                    os.remove(final_pdf_path)

            except Exception as e:
                st.error(f"Analysis failed: {e}")
