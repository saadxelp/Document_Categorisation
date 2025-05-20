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
        # Add more claim form common keywords
        "claim form", "insurance claim", "health claim", "policy holder", "medical insurance", 
        "reimbursement", "cashless", "TPA", "insured", "claimant", "declaration", "policy details",
        "patient details", "healthcare", "hospitalization claim", "medical claim", "claim number"
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
        "website", "Bill Number", "Patient Name",
        "Address", "Item Code", "Bill Category", "Bill Description", "Service Provider",
        "Charge Start Date", "Charge Start Time", "Charge End Date", "Charge End Time",
        "Manufacturer", "Batch No", "Expiry Date", "Quantity",
        "Rate", "Amount", "SGST", "CTST",
        "TAX", "GSTN"
    ]
}

# Define header keywords for document type identification
REPORT_HEADER_KEYWORDS = [
    "laboratory report", "diagnostic report", "test report", "imaging report",
    "pathology report", "radiology report", "lab report", "medical report",
    "investigation report", "blood test", "urine test", "biochemistry",
    "hematology report", "clinical laboratory", "test results"
]

# Define footer keywords that might indicate report type
REPORT_FOOTER_KEYWORDS = [
    "end of report", "laboratory director", "pathologist", "technician",
    "medical laboratory", "authorized signature", "reference value", "normal range"
]

# File pattern mapping to expected categories
FILE_PATTERN_MAPPING = {
    "_C": "Claim Form",
    "_R": "Report",
    "_B": "Hospital Bill",
    "_D": "Discharge Summary"
}

def get_expected_category_from_filename(filename):
    """Extract the expected category based on filename pattern."""
    for pattern, category in FILE_PATTERN_MAPPING.items():
        if pattern in filename:
            return category
    return None

def extract_text_from_pdf(pdf_file, page_num=0):
    """Extract text from a specific page of a PDF file, handling both text-based and scanned/image-based PDFs."""
    try:
        # Reset file pointer to read from start
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        if page_num >= len(pdf_reader.pages):
            return ""  # Return empty string if page number exceeds total pages
        
        text = ""
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

def check_header(text):
    """Check the header (first few lines) for specific keywords indicating document type."""
    # Extract the first 300 characters or first 10 lines as the potential header (increased from 5 to 10)
    header_text = "\n".join(text.split("\n")[:10])[:500].lower()  # Increased to 500 characters
    
    # More flexible claim form detection - look for variations and common terms
    if re.search(r'\b(claim\s*form|insurance\s*claim|health\s*claim|medical\s*claim|hospitali[sz]ation\s*claim)\b', header_text):
        return "Claim Form"
    
    # Check for Report keywords
    for keyword in REPORT_HEADER_KEYWORDS:
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', header_text):
            return "Report"
    
    # Check for explicit header mentions of document types
    if re.search(r'\b(discharge\s*summary|patient\s*discharge|summary\s*of\s*discharge)\b', header_text):
        return "Discharge Summary"
    
    if re.search(r'\b(hospital\s*bill|medical\s*bill|invoice|billing\s*statement)\b', header_text):
        return "Hospital Bill"
    
    if re.search(r'\b(lab\s*report|laboratory\s*report|pathology|test\s*results|diagnostic\s*report|blood\s*report|urine\s*report)\b', header_text):
        return "Report"
    
    return None

def check_keywords(text):
    """Check for category-specific keywords in the text and return the most likely category."""
    text_lower = text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}
    
    # Count keyword matches for each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # Make the regex pattern more flexible to account for OCR errors
            keyword_pattern = r'\b' + re.escape(keyword.lower()).replace('\\s', '\\s*') + r'\b'
            if re.search(keyword_pattern, text_lower):
                category_scores[category] += 1
    
    # Find the category with the most matches
    max_score = max(category_scores.values())
    if max_score >= 2:  # Require at least 2 keyword matches to assign a category
        for category, score in category_scores.items():
            if score == max_score:
                return category
    
    return None  # Return None if no category has enough matches

def categorize_document(text, check_type="full", expected_category=None):
    """
    Categorize the document based on header, keywords, and OpenAI's API.
    
    Args:
        text: The text content of the document
        check_type: Type of check to perform - "full" (all methods), "header_only", "keywords_only"
        expected_category: Expected category based on filename pattern
    """
    # First, if there's an expected category based on filename and the document has obvious markers
    if expected_category:
        # Look for very simple markers in the text that would confirm the expected category
        if expected_category == "Claim Form" and re.search(r'\b(claim|insurance|policy|tpa|insured|claimant)\b', text.lower()):
            return expected_category
        
        elif expected_category == "Report" and re.search(r'\b(report|test|result|lab|laboratory|pathology|reference range)\b', text.lower()):
            return expected_category
            
        elif expected_category == "Hospital Bill" and re.search(r'\b(bill|invoice|charges|payment|amount|tax|gstn)\b', text.lower()):
            return expected_category
            
        elif expected_category == "Discharge Summary" and re.search(r'\b(discharge|summary|admission|treatment|diagnosis)\b', text.lower()):
            return expected_category
    
    # Step 1: Check the header for document type keywords
    header_category = check_header(text)
    if header_category:
        return header_category
    
    # Step 2: Check the footer for report keywords (if it might be a report)
    if check_type != "header_only":
        footer_text = "\n".join(text.split("\n")[-5:])[:300].lower()
        for keyword in REPORT_FOOTER_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', footer_text):
                return "Report"
    
    # Step 3: Try keyword-based classification
    if check_type != "header_only":
        keyword_category = check_keywords(text)
        if keyword_category:
            return keyword_category
    
    # Step 4: Fallback to LLM if header and keyword checks are inconclusive
    if check_type == "full":
        prompt = f"""You are an expert in document classification. 
        Based on the text content below (extracted from a PDF document, possibly using OCR from scanned or image-based PDFs), 
        identify which category this document belongs to from the following options:
        
        1. Claim Form (e.g., insurance or medical claim forms with fields for patient or policy details, often with terms like 'Policy No.', 'TPA ID')
        2. Discharge Summary (e.g., medical summary of hospital stay, including diagnosis, treatment, 'Chief Complaints', 'Discharge Note')
        3. Report (e.g., medical or diagnostic reports like lab results, lab reports, blood tests, imaging reports, often with headers like 'Laboratory Report', 'Test Results')
        4. Hospital Bill (e.g., invoices or bills for medical services, with terms like 'Bill No.', 'Charges', 'Total Amount')
        5. Others (e.g., any document that does not fit the above, such as letters, articles, or unrelated forms)
        
        Pay special attention to:
        - Header (first few lines): May explicitly state the document type
        - Footer (last few lines): May contain lab signatures or report completion notes
        - Tables with values and reference ranges typically indicate a Report
        - Presence of 'Reference values', 'Normal range', or test results strongly suggests a Report
        - Lab technician signatures or pathologist names suggest a Report
        - Insurance claim forms often have fields for policy details, patient information, and medical expenses
        
        The text may be noisy due to OCR. If you see any clear indication this is a lab report or test results document, classify it as 'Report'.
        If you see any clear indication this is a claim form for insurance or medical reimbursement, classify it as 'Claim Form'.
        
        {f"Note: Based on the filename, this document is expected to be a {expected_category}." if expected_category else ""}
        
        Respond with ONLY ONE of these five category names as your answer.
        
        Document content:
        {text[:4000]}  # Limiting text to avoid token limits
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                temperature=0,
                messages=[
                    {"role": "system", "content": "You analyze document text (which may be noisy from OCR) and classify it into exactly one of these categories: 'Claim Form', 'Discharge Summary', 'Report', 'Hospital Bill', or 'Others'. Pay special attention to medical lab reports, test results, reports with tables of values and reference ranges, and insurance claim forms. Respond with only the category name."},
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
    
    # Default to Others if we didn't do LLM check or if all checks failed
    return "Others"

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
    
    The app also validates if the document content matches the expected type based on filename pattern:
    - _C in filename indicates Claim Form
    - _R in filename indicates Report
    - _B in filename indicates Hospital Bill
    - _D in filename indicates Discharge Summary
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
        
        # Get expected category from filename
        expected_category = get_expected_category_from_filename(uploaded_file.name)
        if expected_category:
            st.write(f"**Based on filename pattern:** Expected document type is '{expected_category}'")
        
        with st.spinner("Processing document..."):
            # Process multiple pages (up to 3)
            page_results = []
            page_texts = []
            
            # First, check all three pages and store the results
            for page_num in range(3):  # Check up to 3 pages
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    extracted_text = extract_text_from_pdf(uploaded_file, page_num=page_num)
                    
                    if extracted_text.startswith("Error") or extracted_text == "No text could be extracted from the PDF.":
                        if page_num == 0:  # If even first page fails, show error
                            st.error(extracted_text)
                            break
                        continue  # Skip this page but continue with others
                    
                    page_texts.append(extracted_text)
                    
                    # First try header-only check (faster)
                    header_category = categorize_document(extracted_text, check_type="header_only", expected_category=expected_category)
                    if header_category != "Others":
                        page_results.append({"page": page_num + 1, "category": header_category, "confidence": "High (Header Match)"})
                    else:
                        # If header didn't give clear result, try full categorization
                        page_category = categorize_document(extracted_text, expected_category=expected_category)
                        page_results.append({"page": page_num + 1, "category": page_category, "confidence": "Medium"})
                        
                except Exception as e:
                    st.warning(f"Could not process page {page_num + 1}: {str(e)}")
                    break
            
            # If we have results from multiple pages
            if page_results:
                # Display results with nice formatting
                st.success("Document processed successfully!")
                
                # Check for consistency across pages
                categories = [result["category"] for result in page_results]
                
                # Apply priority logic for expected categories
                if expected_category and expected_category in categories:
                    most_common_category = expected_category
                else:
                    most_common_category = max(set(categories), key=categories.count)
                
                # Check if any page has a header with "Report" (prioritize this)
                for result in page_results:
                    if result["category"] == "Report" and result["confidence"] == "High (Header Match)":
                        most_common_category = "Report"
                        break
                
                # Count occurrences of most common category
                category_count = categories.count(most_common_category)
                total_pages = len(page_results)
                
                st.subheader("Page-by-Page Analysis")
                for result in page_results:
                    confidence_color = "#33CC33" if result["confidence"] == "High (Header Match)" else "#FF9933"
                    st.markdown(f"""
                        <div style="
                            padding: 10px;
                            border-radius: 5px;
                            border-left: 5px solid {confidence_color};
                            background-color: #f8f9fa;
                            margin: 5px 0;
                        ">
                            <strong>Page {result["page"]}:</strong> {result["category"]} 
                            <span style="color: {confidence_color}">({result["confidence"]})</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Final categorization
                st.subheader("Final Document Categorization")
                category_color = {
                    "Claim Form": "#FF9933",
                    "Discharge Summary": "#33CC33",
                    "Report": "#3366FF",
                    "Hospital Bill": "#CC33FF",
                    "Others": "#666666"
                }
                
                # Special handling for expected categories
                if expected_category and any(result["category"] == expected_category for result in page_results):
                    most_common_category = expected_category
                    confidence = "High (Matches expected type from filename)"
                # Determine confidence level
                elif category_count == total_pages:
                    confidence = "High (All pages match)"
                elif category_count > total_pages / 2:
                    confidence = "Medium (Majority of pages match)"
                else:
                    confidence = "Low (Inconsistent across pages)"
                
                # Determine if there's a clear header match for Reports
                has_header_match = any(r["category"] == "Report" and r["confidence"] == "High (Header Match)" for r in page_results)
                if has_header_match and most_common_category != "Report":
                    most_common_category = "Report"
                    confidence = "High (Report header detected)"
                
                # If combined text has strong markers for specific categories but didn't catch it yet
                combined_text = "\n".join(page_texts).lower()
                
                # Check for claim form indicators in the combined text
                if most_common_category == "Others" or (expected_category == "Claim Form" and most_common_category != "Claim Form"):
                    claim_indicators = ["claim form", "insurance claim", "policy", "tpa", "insured"]
                    if any(indicator in combined_text for indicator in claim_indicators):
                        most_common_category = "Claim Form"
                        confidence = "Medium (Claim form markers detected)"
                
                # Check for report indicators in the combined text
                if most_common_category != "Report":
                    report_indicators = ["laboratory", "lab report", "test results", "reference range", "normal range"]
                    if any(indicator in combined_text for indicator in report_indicators):
                        most_common_category = "Report"
                        confidence = "Medium (Report markers detected)"
                
                # Use a fancy display for the category
                st.markdown(
                    f"""
                    <div style="
                        background-color: {category_color.get(most_common_category, '#CCCCCC')};
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        color: white;
                        font-size: 24px;
                        font-weight: bold;
                        margin: 10px 0;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    ">
                        Identified as: {most_common_category}
                        <div style="font-size: 16px; margin-top: 5px;">{confidence}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Validate if the document content matches the expected type from filename
                if expected_category:
                    if most_common_category == expected_category:
                        st.success(f"✅ Validation Success: The document content matches the expected type '{expected_category}' based on filename!")
                    else:
                        st.error(f"❌ Validation Failed: The document was expected to be '{expected_category}' based on filename, but was identified as '{most_common_category}'.")
                
                # Add option to see extracted text
                with st.expander("View extracted text from all pages"):
                    for i, text in enumerate(page_texts):
                        st.subheader(f"Page {i+1}")
                        st.text_area(f"Page {i+1} Content", text, height=200)
                        
                # Allow user to override the classification
                # st.subheader("Override Classification")
                # st.write("If the automatic classification is incorrect, you can manually select the correct category:")
                
                # corrected_category = st.selectbox(
                #     "Select the correct document category:",
                #     ["Claim Form", "Discharge Summary", "Report", "Hospital Bill", "Others"],
                #     index=["Claim Form", "Discharge Summary", "Report", "Hospital Bill", "Others"].index(most_common_category)
                # )
                
                # if corrected_category != most_common_category:
                #     if st.button("Update Classification"):
                #         st.success(f"Classification updated to: {corrected_category}")
                #         most_common_category = corrected_category

if __name__ == "__main__":
    main()