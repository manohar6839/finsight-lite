import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()

# Try to get key from Streamlit Secrets (Cloud) OR Environment Variable (Local)
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("API Key not found. Please set it in Streamlit Secrets.")
else:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_document_with_gemini(file_path, mime_type="application/pdf"):
    # 1. Upload file
    file_ref = genai.upload_file(file_path, mime_type=mime_type)
    
    while file_ref.state.name == "PROCESSING":
        time.sleep(1)
        file_ref = genai.get_file(file_ref.name)

    # 2. Define Prompt
    prompt = """
    Extract the following into raw JSON (no markdown formatting):
    {
        "company_name": "string",
        "fiscal_year": "string",
        "total_revenue": "number",
        "net_income": "number",
        "total_assets": "number",
        "total_liabilities": "number"
    }
    Return null for missing values.
    """

    # 3. Use the working model: gemini-2.5-flash
    model_name = "gemini-2.5-flash" 
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([file_ref, prompt])
        
        # Cleanup file after use
        genai.delete_file(file_ref.name)
        
        return response.text
    except Exception as e:
        # If the API key is not configured (e.g., initial app startup), handle it gracefully
        return json.dumps({
            "error": f"Model Access Failed. Ensure '{model_name}' is correct: {str(e)}", 
            "detail": "Your API key sees newer models than the code expected."
        })

# --- The get_available_models function is now used only for debugging and can be kept in app.py if desired. ---
