import streamlit as st
import PyPDF2
import io
import os
from dotenv import load_dotenv
import openai
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import re

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found in environment variables")
    st.stop()

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

def extract_text_from_pdf(pdf_file, max_pages=3):
    """Extract text from a PDF file, handling both text-based and scanned/image-based PDFs."""
    try:
        # First, try extracting text with PyPDF2 (for text-based PDFs)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
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

def extract_text_from_scanned_pdf(pdf_file, page_num):
    """Extract text from a specific page of a scanned/image-based PDF using OCR."""
    try:
        # Reset file pointer to read from start
        pdf_file.seek(0)
        # Convert PDF page to image
        images = convert_from_bytes(pdf_file.read(), first_page=page_num+1, last_page=page_num+1)
        if not images:
            return ""
        
        # Extract text using OCR
        text = pytesseract.image_to_string(images[0], lang='eng')
        return text + "\n\n"
    except Exception as e:
        return f"Error during OCR extraction: {str(e)}"

def check_keywords(text):
    """Check for category-specific keywords in the text and return the most likely category."""
    text_lower = text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}
    
    # Count keyword matches for each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                category_scores[category] += 1
    
    # Find the category with the most matches
    max_score = max(category_scores.values())
    if max_score >= 2:  # Require at least 2 keyword matches to assign a category
        for category, score in category_scores.items():
            if score == max_score:
                return category
    
    return None  # Return None if no category has enough matches

def categorize_document(text):
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

def main():
    st.set_page_config(
        page_title="Document Categorization App",
        page_icon="📄",
        layout="centered"
    )
    
    st.title("📄 Document Categorization")
    st.subheader("Automatically categorize your PDF documents")
    
    st.write("""
    This application analyzes PDF documents (including scanned or image-based PDFs) and classifies them into one of the following categories:
    - Claim Form
    - Discharge Summary
    - Report
    - Hospital Bill
    - Others
    """)
    
    uploaded_file = st.file_uploader("Upload your PDF document", type=["pdf"])
    
    if uploaded_file is not None:
        # Display file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.write("**File Details:**")
        for key, value in file_details.items():
            st.write(f"- {key}: {value}")
        
        with st.spinner("Processing document..."):
            # Reset file pointer and extract text
            uploaded_file.seek(0)
            extracted_text = extract_text_from_pdf(uploaded_file)
            
            if extracted_text.startswith("Error"):
                st.error(extracted_text)
            elif extracted_text == "No text could be extracted from the PDF.":
                st.error(extracted_text)
            else:
                # Text extraction successful, now categorize
                with st.spinner("Categorizing document..."):
                    category = categorize_document(extracted_text)
                
                # Display results with nice formatting
                st.success("Document processed successfully!")
                
                st.subheader("Document Category")
                category_color = {
                    "Claim Form": "#FF9933",
                    "Discharge Summary": "#33CC33",
                    "Report": "#3366FF",
                    "Hospital Bill": "#CC33FF",
                    "Others": "#666666"
                }
                
                # Use a fancy display for the category
                if category in category_color:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: {category_color.get(category, '#CCCCCC')};
                            padding: 20px;
                            border-radius: 10px;
                            text-align: center;
                            color: white;
                            font-size: 24px;
                            font-weight: bold;
                            margin: 10px 0;
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        ">
                            {category}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.write(category)
                
                # Add option to see extracted text
                with st.expander("View extracted text"):
                    st.text_area("Text from first 3 pages", extracted_text, height=300)

if __name__ == "__main__":
    main()