from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import PyPDF2
import io
import os
from dotenv import load_dotenv
import openai
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import re
from typing import Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Document Categorization API",
    description="Automatically categorize PDF and TIFF documents into predefined categories",
    version="1.0.0"
)

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise Exception("OpenAI API key not found in environment variables")

client = openai.OpenAI(api_key=api_key)

# Define keyword lists for each category
CATEGORY_KEYWORDS = {
    "Claim Form": [
        "Name of the Insurance Company", "Address of the Policy issuing Office", "TPA ID", "Policy No.",
    "Name of the Insured Person", "Name of policy owner", "Relationship to the Insured", "Patient Age",
    "Occupation", "Phone Number", "Mobile Number", "Residential address",
    "email ID", "Bank Name", "Account Holder Name", "Branch Name",
    "IFSC Code", "Account Number", "Account Type", "Bank Address",
    "Name of the Disease/ Illness contracted of injury suffered", "Date of Injury sustained or Disease/ Illness first detected",
    "Name of the Hospital/ Nursing Home/ Clinic", "Address of the Hospital/ Nursing Home/ Clinic",
    "Date of Admission", "Time of admission", "Date of Discharge", "Time of Discharge",
    "Name of attending Medical Practitioner", "Address of attending Medical Practitioner", "Qualification", "Telephone",
    "Mobile Number", "Registration No", "Past Insurance", "Date of Policy commencement",
    "If claim for Domically Hospitalization", "Date of Commencement of treatment", "date of Completion of Treatment",
    "Name of attending Medical Practitioner", "Address of attending Medical Practitioner", "Total Amount Claimed",
    ],
    "Discharge Summary": [
            "Patient Name", "Age", "Sex", "W/o",
    "UHId", "IPD No", "Room No.", "Bed No.",
    "Address", "Contact", "Consultant", "MRD No",
    "Admission Type", "Admission Date", "Admission Time", "Discharge Date",
    "Discharge Time", "Date of Surgery", "Chief Complaints", "Reason for admission",
    "In Examinations", "Diagnosis", "Nature of admission", "Past History",
    "Procedure", "Investigations", "Treatment given in Hospital", "Diet",
    "Condition on Discharge", "Discharge Note", "Follow up Note",
    ],
    "Report": [
        "lab results", "diagnostic report", "imaging report", "test results",
        "radiology", "pathology", "findings", "interpretation", "specimen",
        "Patient Name", "IP NO", "Age", "Sex",
        "Lab reference No", "Doctor", "Referred By", "Test Date",
        "Test Name", "Result", "Units", "Reference Range",
        "Remarks"
    ],
    "Hospital Bill": [
        "invoice", "billing statement", "charges", "payment due", "service date",
        "procedure code", "total amount", "insurance payment", "balance due",
        "Pan No", "GSTN", "Bill No.", "IP No",
        "Bill Date", "Bill Time", "Sex", "Name",
        "Patient ID", "Age", "Father Name", "Mother Name",
        "Bed No", "Ward Name", "Address", "Payment Mode",
        "State", "Referred By", "Ward No", "Consultant",
        "LOS", "Admission Date", "Admission Time", "Discharge Date",
        "Discharge Time", "Policy No", "Claim No", "Pan Number",
        "ID Card", "Prepared by", "Contact number-1", "Contact number-2",
        "Contact number-3", "Contact number-4", "Contact number-5", "email id",
        "website","Bill Number", "Patient Name",
        "Address","Item Code", "Bill Category", "Bill Description", "Service Provider",
        "Charge Start Date", "Charge Start Time", "Charge End Date", "Charge End Time",
        "Manufacturer", "Batch No", "Expiry Date", "Quantity",
        "Rate", "Amount", "SGST", "CTST",
        "TAX", "GSTN"
    ]
}

def convert_tiff_to_pdf(tiff_file: bytes) -> bytes:
    """Convert TIFF file to PDF."""
    try:
        # Open TIFF image from bytes
        image = Image.open(io.BytesIO(tiff_file))

        # Create a PDF in memory
        pdf_buffer = io.BytesIO()

        # Handle multi-page TIFF files
        images = []
        try:
            page_count = 0
            while True:
                # Convert image to RGB if it's not already
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                images.append(image.copy())
                page_count += 1
                image.seek(page_count)
        except EOFError:
            # End of pages reached
            pass

        if images:
            # Save all images as a single PDF
            images[0].save(
                pdf_buffer,
                format='PDF',
                save_all=True,
                append_images=images[1:] if len(images) > 1 else []
            )
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()
        else:
            raise Exception("No valid images found in TIFF file")

    except Exception as e:
        raise Exception(f"Error converting TIFF to PDF: {str(e)}")

def extract_text_from_scanned_pdf(pdf_file: bytes, page_num: int) -> str:
    """Extract text from a specific page of a scanned/image-based PDF using OCR."""
    try:
        # Convert PDF page to image
        images = convert_from_bytes(pdf_file, first_page=page_num+1, last_page=page_num+1)
        if not images:
            return ""
        
        # Extract text using OCR
        text = pytesseract.image_to_string(images[0], lang='eng')
        return text + "\n\n"
    except Exception as e:
        return f"Error during OCR extraction: {str(e)}"

def extract_text_from_pdf(pdf_file: bytes, max_pages: int = 3) -> str:
    """Extract text from a PDF file, handling both text-based and scanned/image-based PDFs."""
    try:
        # First, try extracting text with PyPDF2 (for text-based PDFs)
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
        text = ""
        num_pages = min(max_pages, len(pdf_reader.pages))
        
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            extracted = page.extract_text()
            if extracted and extracted.strip():  # Check if meaningful text is extracted
                text += extracted + "\n\n"
            else:
                # If no text is extracted, assume it's a scanned/image-based PDF
                text += extract_text_from_scanned_pdf(pdf_file, page_num)
                
        return text if text.strip() else "No text could be extracted from the PDF."
    except Exception as e:
        return f"Error extracting text: {str(e)}"



def check_keywords(text: str) -> str:
    """Check for category-specific keywords in the text and return the most likely category."""
    text_lower = text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}
    
    # Boost: if specific strong indicators are in the header, add extra score
    header = text_lower.split("\n", 5)[0]  # check top-most line

    if "claim form" in header:
        category_scores["Claim Form"] += 5
    elif "discharge summary" in header:
        category_scores["Discharge Summary"] += 5
    elif "report" in header:
        category_scores["Report"] += 5
    elif "invoice" in header or "hospital bill" in header:
        category_scores["Hospital Bill"] += 5
    
    # Count keyword matches for each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                category_scores[category] += 1

    # Return category with highest score
    max_score = max(category_scores.values())
    if max_score >= 2:
        for category, score in category_scores.items():
            if score == max_score:
                return category

    return None


def categorize_document(text: str) -> str:
    """Categorize the document based on keywords and OpenAI's API."""
    # First, try keyword-based classification
    keyword_category = check_keywords(text)
    if keyword_category:
        return keyword_category
    
    # Fallback to LLM if keyword check is inconclusive
    prompt = f"""You are an expert in document classification. 
    Based on the text content below (extracted from a PDF document, possibly using OCR from scanned or image-based PDFs), 
    identify which category this document belongs to from the following options:
    
    1. Claim Form (e.g., insurance or medical claim forms with fields for patient or policy details)
    2. Discharge Summary (e.g., medical summary of hospital stay, including diagnosis and treatment)
    3. Report (e.g., medical or diagnostic reports like lab results or imaging reports)
    4. Hospital Bill (e.g., invoices or bills for medical services)
    5. Others (e.g., any document that does not fit the above, such as letters, articles, or unrelated forms)
    
    The text may be noisy due to OCR, so focus on key terms, structure, or patterns that indicate the document type. 
    If the document does not clearly match Claim Form, Discharge Summary, Report, or Hospital Bill, classify it as 'Others'.
    Respond with ONLY ONE of these five category names as your answer.
    
    Document content:
    {text[:4000]}  # Limiting text to avoid token limits
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using GPT-3.5 Turbo
            temperature=0,
            messages=[
                {"role": "system", "content": "You analyze document text (which may be noisy from OCR) and classify it into exactly one of these categories: 'Claim Form', 'Discharge Summary', 'Report', 'Hospital Bill', or 'Others'. If the document does not clearly match the first four categories, return 'Others'. Respond with only the category name."},
                {"role": "user", "content": prompt}
            ]
        )
        category = response.choices[0].message.content.strip()
        
        # Ensure the response is one of the five categories
        valid_categories = ["Claim Form", "Discharge Summary", "Report", "Hospital Bill", "Others"]
        for valid_cat in valid_categories:
            if valid_cat.lower() in category.lower():
                return valid_cat
                
        return "Others"  # Default to Others if no valid category is matched
    except Exception as e:
        return f"Error during categorization: {str(e)}"

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Document Categorization API",
        "version": "1.0.0",
        "description": "Upload PDF or TIFF documents to automatically categorize them",
        "endpoints": {
            "POST /categorize": "Upload and categorize a PDF or TIFF document",
            "GET /health": "Health check endpoint"
        },
        "supported_formats": ["PDF", "TIFF", "TIF"],
        "note": "TIFF files are automatically converted to PDF before processing"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}

@app.post("/categorize")
async def categorize_document_file(file: UploadFile = File(...)):
    """
    Categorize a PDF or TIFF document.
    
    - **file**: PDF or TIFF file to be categorized
    
    TIFF files are automatically converted to PDF before processing.
    Returns the document category and extracted text.
    """
    # Validate file type
    allowed_types = ["application/pdf", "image/tiff", "image/tif"]
    if file.content_type not in allowed_types:
        # Also check by filename extension as a fallback
        filename_lower = file.filename.lower() if file.filename else ""
        if not (filename_lower.endswith('.pdf') or filename_lower.endswith(('.tiff', '.tif'))):
            raise HTTPException(
                status_code=400, 
                detail="Only PDF and TIFF files are supported"
            )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Determine if it's a TIFF file and convert to PDF if needed
        is_tiff = False
        if (file.content_type in ["image/tiff", "image/tif"] or 
            (file.filename and file.filename.lower().endswith(('.tiff', '.tif')))):
            is_tiff = True
            # Convert TIFF to PDF
            file_content = convert_tiff_to_pdf(file_content)
        
        # Extract text from PDF (original or converted)
        extracted_text = extract_text_from_pdf(file_content)
        
        if extracted_text.startswith("Error"):
            raise HTTPException(status_code=500, detail=extracted_text)
        elif "No text could be extracted" in extracted_text:
            raise HTTPException(status_code=422, detail=extracted_text)
        
        # Categorize document
        category = categorize_document(extracted_text)
        
        # Prepare response
        response_data = {
            "filename": file.filename,
            "original_file_type": "TIFF" if is_tiff else "PDF",
            "processed_as": "PDF",
            "file_size_kb": round(len(await file.read()) / 1024, 2) if not is_tiff else round(len(file_content) / 1024, 2),
            "category": category,
            # "extracted_text": extracted_text,
            "status": "success"
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while processing the document: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)