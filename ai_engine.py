import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_available_models():
    """Debugging tool to list what models your API key can actually see."""
    return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

def analyze_document_with_gemini(file_path, mime_type="application/pdf"):
    # Upload file
    file_ref = genai.upload_file(file_path, mime_type=mime_type)
    
    while file_ref.state.name == "PROCESSING":
        time.sleep(1)
        file_ref = genai.get_file(file_ref.name)

    prompt = """
    Extract the following into raw JSON (no markdown):
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

    # TRY-CATCH BLOCK FOR MODEL NAMING
    try:
        # Primary attempt: Standard name
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([file_ref, prompt])
    except Exception:
        # Fallback attempt: Specific version (often fixes 404s)
        print("Retrying with gemini-1.5-flash-latest...")
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content([file_ref, prompt])

    return response.text
