import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_available_models():
    """Lists models your API key can actually access."""
    try:
        return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        return [f"Error listing models: {str(e)}"]

def analyze_document_with_gemini(file_path, mime_type="application/pdf"):
    # 1. Upload file
    file_ref = genai.upload_file(file_path, mime_type=mime_type)
    
    # Wait for processing
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

    # 3. Robust Model Selection
    # We try the standard name first. If that fails, we try the specific version.
    try:
        model_name = "gemini-1.5-flash" 
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([file_ref, prompt])
    except Exception as e:
        print(f"First attempt failed with {model_name}: {e}")
        try:
            # Fallback to the specific numbered version which is often more stable
            model_name = "models/gemini-1.5-flash-001" 
            print(f"Retrying with {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([file_ref, prompt])
        except Exception as final_e:
            # If both fail, returning the error to the UI is helpful
            return f'{{"error": "Model access failed. Your API key sees: {get_available_models()}"}}'

    return response.text
