import os
import streamlit as st
import google.generativeai as genai
import time
import json

# --- Configuration (Runs once when the app starts) ---

# Fetch API key from Streamlit secrets (preferred) or environment variables
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if api_key:
    # Use a try-except block in case configure fails for some reason
    try:
        genai.configure(api_key=api_key)
        st.session_state['gemini_configured'] = True
    except Exception as e:
        st.session_state['gemini_configured'] = False
        st.error(f"Failed to configure Gemini API. Check your key and network. Error: {e}")
else:
    st.session_state['gemini_configured'] = False
    
# --- Utility Functions ---

def get_available_models():
    """Lists models your API key can actually access for debugging."""
    if not st.session_state.get('gemini_configured', False):
        return ["API Key not configured. Cannot list models."]
    try:
        # Filter for models that can generate content (text/vision)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return models
    except Exception as e:
        return [f"Error listing models: {str(e)}"]

def analyze_document_with_gemini(file_path, mime_type="application/pdf"):
    """Uploads a file, sends it to Gemini, and returns the raw response text."""
    if not st.session_state.get('gemini_configured', False):
        return json.dumps({"error": "Gemini API is not configured."})

    model_name = "gemini-2.5-flash"  # Use the correct, available model

    try:
        # 1. Upload file
        st.info(f"Uploading file to Gemini... ({os.path.basename(file_path)})")
        file_ref = genai.upload_file(file_path, mime_type=mime_type)
        
        # Wait for file processing to complete
        while file_ref.state.name == "PROCESSING":
            time.sleep(1)
            file_ref = genai.get_file(file_ref.name)
        
        if file_ref.state.name != "ACTIVE":
            genai.delete_file(file_ref.name)
            return json.dumps({"error": f"File processing failed on the API side. State: {file_ref.state.name}"})

        st.info("File uploaded and active. Starting analysis...")

        # 2. Define Structured Output Prompt (Crucial for reliable JSON)
        prompt = """
        You are an expert financial data extraction tool. Analyze the provided financial document.
        Extract the following fields into a single, raw JSON object. Do not include any text, preambles, or markdown formatting (e.g., no ```json ```).
        If a value is not found, return null for that field.

        Output Schema:
        {
            "company_name": "string",
            "fiscal_year": "string",
            "total_revenue": "number (in millions or billions, specify units)",
            "net_income": "number (in millions or billions, specify units)",
            "total_assets": "number (in millions or billions, specify units)",
            "total_liabilities": "number (in millions or billions, specify units)"
        }
        """

        # 3. Generate Content
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([file_ref, prompt])
        
        # 4. Cleanup API file before returning
        genai.delete_file(file_ref.name)

        # 5. Check for empty response (Indicates a service error/timeout)
        if not response.text:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return json.dumps({"error": f"AI Blocked Request: {response.prompt_feedback.block_reason.name}"})
            else:
                return json.dumps({"error": "AI returned an empty response. Try simplifying the prompt or file."})

        return response.text
        
    except Exception as e:
        # Attempt to clean up the file if an error occurred after upload but before deletion
        if 'file_ref' in locals() and file_ref:
             genai.delete_file(file_ref.name)
        return json.dumps({"error": f"An unexpected error occurred during API call: {str(e)}"})

# Note: The raw JSON string is returned here, and the cleaning/parsing happens in app.py
