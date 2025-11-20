import streamlit as st
import json
import pandas as pd
import tempfile
# Import the function from Step B (assuming it's in ai_engine.py)
from ai_engine import analyze_document_with_gemini

st.set_page_config(page_title="FinSight Lite", layout="wide")

st.title("🤖 FinSight Lite: AI Annual Report Analyzer")
st.markdown("Using **Gemini 1.5 Flash** for $0 cost extraction.")

# 1. File Upload Section
uploaded_file = st.file_uploader("Upload Annual Report (PDF)", type="pdf")

if uploaded_file:
    # Save to temp file because API needs a path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    col1, col2 = st.columns([1, 1])

    with col1:
        st.info("📄 Document Preview")
        # Displaying PDFs in streamlit is simple with an iframe or image
        st.write(f"Processing: {uploaded_file.name}")

    with col2:
        st.info("📊 Extracted Data")
        if st.button("Analyze Report"):
            with st.spinner("AI is reading the document..."):
                try:
                    # Call the AI
                    raw_json = analyze_document_with_gemini(tmp_path)
                    
                    # Parse JSON
                    data = json.loads(raw_json)
                    
                    # Interactive Disambiguation (Edit Mode)
                    # Streamlit's data_editor allows users to fix AI mistakes instantly!
                    df = pd.DataFrame([data]).T.reset_index()
                    df.columns = ["Metric", "Value"]
                    
                    edited_df = st.data_editor(df, num_rows="dynamic")
                    
                    st.success("Analysis Complete!")
                    
                    # Download Button
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download CSV",
                        csv,
                        "financial_data.csv",
                        "text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"Error: {e}")
