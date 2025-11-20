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

# --- Helper: Parse Page Ranges ---
def parse_page_selection(selection_str, max_pages):
    """
    Parses a string like "1-3, 5, 8-10" into a list of 0-based indices.
    """
    if not selection_str.strip():
        return None
    
    selected_pages = set()
    try:
        parts = selection_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                # Convert to 0-based index and handle ranges
                selected_pages.update(range(start - 1, end))
            else:
                selected_pages.add(int(part) - 1)
    except ValueError:
        st.error("⚠️ Invalid page format. Use '1-3, 5' format.")
        return None

    # Filter out out-of-bounds pages
    valid_pages = sorted([p for p in selected_pages if 0 <= p < max_pages])
    return valid_pages

# --- Helper: Extract Specific Pages ---
def extract_pages_from_pdf(input_path, page_indices):
    """
    Creates a new temporary PDF containing only the selected pages.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for idx in page_indices:
        writer.add_page(reader.pages[idx])
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
        writer.write(tmp_out)
        return tmp_out.name

# --- Helper: Save Uploaded File ---
def save_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

# --- Helper: Download PDF from URL ---
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

# --- Main Interface ---
tab1, tab2 = st.tabs(["📂 Upload PDF", "🔗 Paste Report URL"])

raw_pdf_path = None
file_name = None

# --- TAB 1: Upload ---
with tab1:
    uploaded_file = st.file_uploader("Upload Annual Report", type="pdf")
    if uploaded_file:
        raw_pdf_path = save_uploaded_file(uploaded_file)
        file_name = uploaded_file.name

# --- TAB 2: URL ---
with tab2:
    url_input = st.text_input("Paste Report URL:", placeholder="https://example.com/report.pdf")
    if url_input and st.button("Fetch PDF"):
        with st.spinner("Downloading..."):
            path = download_pdf_from_url(url_input)
            if path:
                raw_pdf_path = path
                file_name = "url_document.pdf"
                st.success("✅ Downloaded!")

# --- Processing Section ---
if raw_pdf_path:
    st.divider()
    
    # 1. Get Page Count
    try:
        reader = PdfReader(raw_pdf_path)
        total_pages = len(reader.pages)
    except Exception:
        st.error("Error reading PDF structure.")
        total_pages = 0

    col1, col2 = st.columns([1, 2])

    with col1:
        st.info(f"📄 **{file_name}** ({total_pages} Pages)")
        
        # --- PAGE SELECTION INPUT ---
        st.markdown("### ✂️ Page Selection")
        page_selection = st.text_input(
            "Enter page numbers to analyze:", 
            placeholder="e.g., 1, 3-5, 10",
            help="Leave empty to analyze the entire document."
        )
        
        final_pdf_path = raw_pdf_path
        selected_indices = None
        
        if page_selection:
            selected_indices = parse_page_selection(page_selection, total_pages)
            if selected_indices:
                st.caption(f"✅ Analyzing {len(selected_indices)} specific pages.")
            else:
                st.caption("⚠️ Invalid range or full document selected.")

    with col2:
        st.subheader("📊 Extraction Results")
        if st.button("Analyze Report", type="primary"):
            with st.spinner("Processing..."):
                try:
                    # Pre-processing: Slice PDF if pages were selected
                    if selected_indices:
                        final_pdf_path = extract_pages_from_pdf(raw_pdf_path, selected_indices)
                    
                    # AI Processing
                    raw_json = analyze_document_with_gemini(final_pdf_path)
                    data = json.loads(raw_json)
                    
                    # Display Data
                    df = pd.DataFrame([data]).T.reset_index()
                    df.columns = ["Metric", "Value"]
                    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
                    
                    # Cleanup Sliced PDF if it was created
                    if selected_indices and final_pdf_path != raw_pdf_path:
                        os.remove(final_pdf_path)

                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                
                finally:
                    # Always clean up the raw download/upload
                    # Note: In a real app, you might want to keep raw_pdf_path 
                    # longer if the user wants to re-run with different pages.
                    pass
