import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_document_with_gemini(file_path, mime_type="application/pdf"):
    # 1. Upload the file to Gemini (Vision-First ingestion)
    # This bypasses local OCR entirely. The model "sees" the PDF.
    print(f"Uploading {file_path}...")
    file_ref = genai.upload_file(file_path, mime_type=mime_type)
    
    # Wait for processing (usually instant for small files)
    while file_ref.state.name == "PROCESSING":
        print("Processing file...")
        time.sleep(2)
        file_ref = genai.get_file(file_ref.name)

    # 2. Define the Extraction Schema (The "Configuration")
    # We want strict JSON output.
    prompt = """
    You are a financial analyst. Analyze this Annual Report PDF.
    Extract the following data points into a strictly valid JSON format:
    
    1. "company_name": String
    2. "fiscal_year": String
    3. "total_revenue": Number (consolidated)
    4. "net_income": Number
    5. "total_assets": Number
    6. "total_liabilities": Number
    
    If a value is not found, return null. 
    Do not include markdown formatting like ```json. Just return the raw JSON string.
    """

    # 3. The Cheap & Fast Model
    # Gemini 1.5 Flash is optimized for high-volume, low-latency tasks.
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    response = model.generate_content([file_ref, prompt])
    
    # Cleanup: Delete file from cloud to respect privacy/storage
    # genai.delete_file(file_ref.name)
    
    return response.text
