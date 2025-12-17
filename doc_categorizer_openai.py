import streamlit as st
import PyPDF2
import io
import os
from dotenv import load_dotenv
import openai
import google.generativeai as genai
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import re
from prompts import get_document_classification_prompt, get_openai_system_message

# Load environment variables from .env file
load_dotenv()

# Initialize API clients
openai_api_key = os.environ.get("OPENAI_API_KEY")
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# Initialize OpenAI client
openai_client = None
if openai_api_key:
    openai_client = openai.OpenAI(api_key=openai_api_key)

# Initialize Gemini client
gemini_client = None
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_client = genai.GenerativeModel('gemini-pro')

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
        "Claim Form", "Insurance Claim", "Medical Claim", "Health Claim", "Reimbursement Claim",
        "Policy Holder", "Policy Number", "Sum Insured", "Insured Person", "Insurance Details",
        "Claim Number", "Claim Reference", "Claim Amount", "Claim Date", "Claim Submission",
        "Insurer", "Insurance Company", "Health Insurance", "Medical Insurance", "Policy Details",
        "Claimant", "Claimant Name", "Claimant Address", "Claimant Contact", "Claimant Signature",
        "Declaration", "I hereby declare", "Signature of the Insured", "Date of Declaration",
        "CLAIM NO", "CLAIM NUMBER", "REF NO", "REFERENCE NUMBER", "CLAIM REFERENCE",
        "TOTAL AMOUNT CLAIMED", "AMOUNT CLAIMED", "REIMBURSEMENT", "AFTER HOSPITALIZATION",
        "INURRED", "SPENT", "PAID", "UNDERWENT", "HOSPITALIZED", "TREATED"
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
        "Discharge Summary", "Clinical Summary", "Advice", "Regd No", "Ward", 
        "Fell down", "Admitted for", "Treatment", "Discussed", "Consultant", 
        "Duty Medical Officer", "DMO", "Follow-up", "Follow up", "Medication", 
        "Tab", "Cap", "Syrup", "Inj", "Ointment", "Drops"
    ],
    "Reports": [
        "lab results", "diagnostic report", "imaging report", "test results",
        "radiology", "pathology", "findings", "interpretation", "specimen",
        "Patient Name", "IP NO", "Age", "Sex",
        "Lab reference No", "Doctor", "Referred By", "Test Date",
        "Test Name", "Result", "Units", "Reference Range",
        "Remarks", "Normal Range", "Biological Reference Interval", 
        "Method", "Specimen", "Collection Date", "Reporting Date",
        "Test Report", "Laboratory", "Diagnostics", "Test Code", "Patient ID",
        "Accession No", "Drawn", "Received", "Reported", "Referring Doctor",
        "Test Report Status", "Final", "Results", "Biochemistry", "Glucose",
        "Plasma", "Urine", "Serum", "Blood", "mg/dL", "mmol/L", "Interpretation",
        "Spectrophotometry", "Immunoassay", "Microbiology", "Hematology", "Cytology"
    ],
    "Cancelled cheque": [
        "Payee_Name", "A_C_Number", "Bank_Name", "Ifsc", "Micr", "Branch_Name", "Cheque_Number",
        "Payee Name", "A/C Number", "Account Number", "Bank Name", "IFSC", "MICR", "Branch Name", 
        "Cheque Number", "Cancelled Cheque", "Account Holder", "Bank", "Branch", "IFSC Code"
    ],
    "Hospital Bills": [
        "invoice", "billing statement", "charges", "payment due", "service date",
        "procedure code", "total amount", "insurance payment", "balance due",
        "Pan No", "GSTN", "Bill No.", "IP No", "final bill",
        "Bill Date", "Bill Time", "Sex", "Name",
        "Patient ID", "Age", "Father Name", "Mother Name",
        "Bed No", "Ward Name", "Address", "Payment Mode",
        "State", "Referred By", "Ward No", "Consultant",
        "LOS", "Admission Date", "Admission Time", "Discharge Date",
        "Discharge Time", "Policy No", "Claim No", "Pan Number",
        "ID Card", "Prepared by", "Contact number-1", "Contact number-2",
        "Contact number-3", "Contact number-4", "Contact number-5", "email id",
        "website", "Bill Number", "Patient Name", "hospital",
        "Address", "Item Code", "Bill Category", "Bill Description", "Service Provider",
        "Charge Start Date", "Charge Start Time", "Charge End Date", "Charge End Time",
        "Manufacturer", "Batch No", "Expiry Date", "Quantity",
        "Rate", "Amount", "SGST", "CTST",
        "TAX", "GSTN", "bed charges", "room charges", "doctor consultancy", "pathological investigation",
        "cardiological investigation", "balance due", "net bill amt", "total bill amt",
        "FINAL BILL", "BILL NO", "BILL NUMBER", "TOTAL BILL AMT", "NET BILL AMT",
        "HOSPITAL BILL", "INVOICE", "BILLING STATEMENT", "CHARGES", "PAYMENT DUE"
    ],
    "Pharmacy Bills": [
        "Name_Of_Biller", "Address_Of_Biller", "Address_Lines", "City", "State", "Pincode", "Name_Of_Patient", "Bill_Date", "Bill_No.", "Treating_Dr", "Bill_Items", "Sr_No", "Batch_No", "Expiry_No", "Description", "Unit", "Unit_Price", "Discount", "Actual_Price", "Is_Nme", "Is_Returned", "Expense_Category", "Expense_Code", "Name_Of_Implant", "Implant_Sticker_Number", "Total_Discount", "Total_Amount",
        "Pharmacy", "Drug", "Medicine", "Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Prescription", "Dosage", "MRP", "Retail Price", "Medication", "Chemist", "Pharmacy Bill", "Medical Store", "Drugstore", "Dispensary", "Rx", "Prescribed", "Refill"
    ],
    "Diagnostic Bills": [
        "Name_Of_Biller", "Address_Of_Biller", "Address_Lines", "City", "State", "Pincode", "Bill_Date", "Bill_No", "Bill_Line_Items", "Name_Of_Test", "Price", "Is_Nme", "Total_Discount", "Total_Amount_Paid"
    ],
    "KYC": [
        "Proof_Type", "Name", "Date_Of_Birth", "Is_Id_Proof", "Is_Address_Proof", 
        "KYC", "Know Your Customer", "Customer Information", "Identity Proof", "Address Proof", 
        "PAN", "Aadhaar", "Passport", "Voter ID", "Driving License", "CERSAI", "Central KYC Registry", 
        "Application Form", "Customer Details", "Personal Details", "Identity and Address", 
        "Current Address", "Permanent Address", "Photograph", "Signature", "Date of Birth",
        "Mother Name", "Father Name", "Gender", "Marital Status", "Nationality", "Occupation",
        "Form 60", "Form 61", "E-KYC", "Biometric", "Video KYC", "Digital KYC", "KYC Verification",
        "KYC Compliance", "KYC Documents", "KYC Process", "KYC Update", "KYC Registration",
        "Applicant", "Applicant Details", "Customer ID", "Account Type", "Account Number",
        "IFSC Code", "MICR Code", "Branch Name", "Branch Code", "Bank Name", "Bank Account",
        "Residential Status", "Correspondence Address", "Proof of Identity", "Proof of Address"
    ],
    "Pre-Auth form C": [
        "Family_Physician", "Exists", "Name", "Insured_Card_Id_Number", "Policy_Number_Or_Name_Of_Corporate", "Employee_Id", "Contact_No", "Present_Illness", "Duration_Of_Present_Ailment", "Date_Of_First_Consultation", "Provisional_Diagnosis", "Proposed_Line_Of_Treatment", "Name_Of_Surgery_If_Yes", "Date_Of_Admission", "Room_Type", "Per_Day_Room_Nursing_Diet_Charges", "Expected_Cost_Diagnostics_Investigation", "Icu_Charges", "Ot_Charges", "Surgeon_Anaesthetist_Consultation_Charges", "Medicine_Consumables_Implant_Charges", "Other_Hospital_Expenses", "All_Inclusive_Package_Charges", "Total_Expected_Cost", "Past_History_Of_Chronic_Illnesses", "Diabetes", "Hypertension", "Heart_Disease", "Hyperlipidemia", "Osteoarthritis", "Asthma_Copd_Bronchitis", "Cancer", "Alcohol_Drug_Abuse", "Any_Hiv_Or_Std_Related_Ailments", "Treating_Dr_Name", "Qualification", "Registration_No", "Patient_Contact_No", "Patient_Alternate_Contact_No", "Patient_Email_Id", "Patient_Alternate_Email_Id", "hypertension", "registration_no", "any_other_ailments",
        "Pre-Approval Certificate", "Pre-Auth", "Pre-Authorization", "Authorization Certificate", "Approval Certificate",
        "Estimated Expenses", "Authorized Limit", "Proposed Date Of Hospitalization", "Class Of Accommodation",
        "Estimated Expenses", "Amount Payable by Insured", "Compulsory Deduction", "Co-Payment", "Authorized Limit",
        "PAC No", "Medical Superintendent", "Ref no", "Policy No", "ID Card Number", "Nature Of Illness",
        "Ailment", "Otolaryngology", "Proposed Date Of Hospitalization", "Estimated Duration", "Treating Doctor",
        "REQUEST FOR CASHLESS HOSPITALISATION", "REQUEST FOR CASHLESS HOSPITALIZATION", "TO BE FILLED BY INSURED",
        "TO BE FILLED BY INSURED PATIENT", "PROPOSED TREATMENT", "ESTIMATED COST", "EXPECTED COST",
        "PROPOSED DATE", "ESTIMATED DURATION", "AUTHORIZED AMOUNT", "PRE-APPROVAL", "PRE-AUTH FORM",
        "CASH LESS", "CASHLESS", "BEFORE HOSPITALIZATION", "PRE-HOSPITALIZATION"
    ]
}

# Mapping of file types to their extensions
FILE_TYPE_EXTENSIONS = {
    "Claim Form": "C",
    "Discharge Summary": "D",
    "Reports": "R",
    "Cancelled cheque": "Q",
    "Hospital Bills": "B",
    "Pharmacy Bills": "P",
    "Diagnostic Bills": "I",
    "KYC": "K",
    "Pre-Auth form C": "PF"
}


def convert_tiff_to_pdf(tiff_file_bytes: bytes) -> bytes:
    """Convert TIFF file to PDF."""
    try:
        # Open TIFF image from bytes
        image = Image.open(io.BytesIO(tiff_file_bytes))

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


def extract_text_from_pdf(pdf_file, max_pages=None):
    """Extract text from a PDF file, handling both text-based and scanned/image-based PDFs.
    Returns a list of text for each page."""
    try:
        # First, try extracting text with PyPDF2 (for text-based PDFs)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)
        
        # If max_pages is not specified, process all pages
        if max_pages is None:
            max_pages = total_pages
        else:
            max_pages = min(max_pages, total_pages)
        
        page_texts = []
        
        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            extracted = page.extract_text()
            if extracted and extracted.strip():  # Check if meaningful text is extracted
                page_texts.append(extracted)
            else:
                # If no text is extracted, assume it's a scanned/image-based PDF
                scanned_text = extract_text_from_scanned_pdf(pdf_file, page_num)
                page_texts.append(scanned_text)

        return page_texts if page_texts else ["No text could be extracted from the PDF."]
    except Exception as e:
        return [f"Error extracting text: {str(e)}"]


def extract_text_from_scanned_pdf(pdf_file, page_num):
    """Extract text from a specific page of a scanned/image-based PDF using OCR."""
    try:
        # Reset file pointer to read from start
        pdf_file.seek(0)
        # Convert PDF page to image
        images = convert_from_bytes(
            pdf_file.read(), first_page=page_num+1, last_page=page_num+1)
        if not images:
            return ""

        # Extract text using OCR
        text = pytesseract.image_to_string(images[0], lang='eng')
        return text + "\n\n"
    except Exception as e:
        return f"Error during OCR extraction: {str(e)}"


def extract_text_from_tiff(tiff_file_bytes: bytes, max_pages=3) -> str:
    """Extract text from TIFF file using OCR."""
    try:
        # Open TIFF image from bytes
        image = Image.open(io.BytesIO(tiff_file_bytes))

        text = ""
        page_count = 0

        try:
            while page_count < max_pages:
                # Extract text using OCR from current page
                page_text = pytesseract.image_to_string(image, lang='eng')
                if page_text and page_text.strip():
                    text += page_text + "\n\n"

                page_count += 1
                try:
                    image.seek(page_count)
                except EOFError:
                    # End of pages reached
                    break
        except EOFError:
            # Single page TIFF or end of pages
            pass

        return text if text.strip() else "No text could be extracted from the TIFF file."
    except Exception as e:
        return f"Error extracting text from TIFF: {str(e)}"


def preprocess_text_for_header_detection(text):
    """
    Preprocess text to better detect headers, especially for OCR text which might have spacing issues.
    """
    # Convert multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    # Join hyphenated line breaks (e.g., "HOSPITALI-\nSATION")
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    
    # Common OCR errors in discharge summaries
    text = text.replace('0ISCHARGE', 'DISCHARGE')
    text = text.replace('DlSCHARGE', 'DISCHARGE')
    text = text.replace('D1SCHARGE', 'DISCHARGE')
    text = text.replace('SUMHARY', 'SUMMARY')
    text = text.replace('SUMMARV', 'SUMMARY')
    text = text.replace('SUMM4RY', 'SUMMARY')
    
    # Common OCR errors in claim forms
    text = text.replace('CLA1M', 'CLAIM')
    text = text.replace('CLAlM', 'CLAIM')
    text = text.replace('CLAM', 'CLAIM')
    text = text.replace('F0RM', 'FORM')
    text = text.replace('FORN', 'FORM')
    text = text.replace('F0RN', 'FORM')
    text = text.replace('N0', 'NO')  # Added for claim number
    text = text.replace('N0.', 'NO.')  # Added for claim number
    text = text.replace('N0:', 'NO:')  # Added for claim number
    text = text.replace('CLA1M NO', 'CLAIM NO')  # Added for claim number
    text = text.replace('CLAlM NO', 'CLAIM NO')  # Added for claim number
    text = text.replace('CLAM NO', 'CLAIM NO')  # Added for claim number
    text = text.replace('REF N0', 'REF NO')  # Added for reference number
    text = text.replace('REF.N0', 'REF.NO')  # Added for reference number
    text = text.replace('REF.N0.', 'REF.NO.')  # Added for reference number
    text = text.replace('REF.N0:', 'REF.NO:')  # Added for reference number
    text = text.replace('REF N0.', 'REF NO.')  # Added for reference number
    text = text.replace('REF N0:', 'REF NO:')  # Added for reference number
    
    # Common OCR errors in pre-authorization forms
    text = text.replace('PRE-APPR0VAL', 'PRE-APPROVAL')
    text = text.replace('PRE-APPR0VAl', 'PRE-APPROVAL')
    text = text.replace('PRE-APPROVAl', 'PRE-APPROVAL')
    text = text.replace('PRE-AUTHORIZATI0N', 'PRE-AUTHORIZATION')
    text = text.replace('PRE-AUTHORlZATION', 'PRE-AUTHORIZATION')
    text = text.replace('PRE-AUTHORIZAT1ON', 'PRE-AUTHORIZATION')
    text = text.replace('CERT1FICATE', 'CERTIFICATE')
    text = text.replace('CERTlFICATE', 'CERTIFICATE')
    text = text.replace('CERTIF1CATE', 'CERTIFICATE')
    text = text.replace('REOUEST', 'REQUEST')  # Common OCR error
    text = text.replace('H0SPITALIZATION', 'HOSPITALIZATION')  # Common OCR error
    text = text.replace('H0SPlTALIZATION', 'HOSPITALIZATION')  # Common OCR error
    text = text.replace('HOSPlTALIZATION', 'HOSPITALIZATION')  # Common OCR error
    text = text.replace('CASH LESS', 'CASHLESS')  # Normalize cashless
    
    # Fix spacing around common header terms
    text = re.sub(r'DIS\s*CHARGE\s*SUM\s*MARY', 'DISCHARGE SUMMARY', text, flags=re.IGNORECASE)
    text = re.sub(r'DIS\s*CHARGE', 'DISCHARGE', text, flags=re.IGNORECASE)
    text = re.sub(r'SUM\s*MARY', 'SUMMARY', text, flags=re.IGNORECASE)
    
    # Fix spacing around claim form terms
    text = re.sub(r'CLA\s*IM\s*FO\s*RM', 'CLAIM FORM', text, flags=re.IGNORECASE)
    text = re.sub(r'CLA\s*IM', 'CLAIM', text, flags=re.IGNORECASE)
    text = re.sub(r'FO\s*RM', 'FORM', text, flags=re.IGNORECASE)
    text = re.sub(r'INS\s*UR\s*ANCE\s*CLA\s*IM', 'INSURANCE CLAIM', text, flags=re.IGNORECASE)
    text = re.sub(r'MED\s*ICAL\s*CLA\s*IM', 'MEDICAL CLAIM', text, flags=re.IGNORECASE)
    text = re.sub(r'HEA\s*LTH\s*CLA\s*IM', 'HEALTH CLAIM', text, flags=re.IGNORECASE)
    
    # Fix spacing around claim number references
    text = re.sub(r'CLA\s*IM\s*N[O0]\s*[.:]?', 'CLAIM NO:', text, flags=re.IGNORECASE)
    text = re.sub(r'REF\s*[.:]?\s*N[O0]\s*[.:]?', 'REF NO:', text, flags=re.IGNORECASE)
    text = re.sub(r'REF\s*[.:]?\s*N[O0]\s*[.:]?\s*/\s*CLA\s*IM\s*N[O0]\s*[.:]?', 'REF NO:/CLAIM NO:', text, flags=re.IGNORECASE)
    
    # Fix spacing around pre-authorization terms
    text = re.sub(r'PRE[\s\-]*APP\s*ROVAL', 'PRE-APPROVAL', text, flags=re.IGNORECASE)
    text = re.sub(r'PRE[\s\-]*AUTH\s*ORIZATION', 'PRE-AUTHORIZATION', text, flags=re.IGNORECASE)
    text = re.sub(r'APP\s*ROVAL\s*CERT\s*IFICATE', 'APPROVAL CERTIFICATE', text, flags=re.IGNORECASE)
    text = re.sub(r'AUTH\s*ORIZATION\s*CERT\s*IFICATE', 'AUTHORIZATION CERTIFICATE', text, flags=re.IGNORECASE)
    text = re.sub(r'RE\s*QUEST\s*FOR\s*CASH\s*LESS', 'REQUEST FOR CASHLESS', text, flags=re.IGNORECASE)
    text = re.sub(r'CASH\s*LESS\s*HOSPITAL', 'CASHLESS HOSPITAL', text, flags=re.IGNORECASE)
    text = re.sub(r'TO\s*BE\s*FILLED\s*BY\s*INSURED', 'TO BE FILLED BY INSURED', text, flags=re.IGNORECASE)
    
    # Fix spacing around KYC terms
    text = re.sub(r'CEN\s*TRAL\s*KYC\s*REG\s*ISTRY', 'CENTRAL KYC REGISTRY', text, flags=re.IGNORECASE)
    text = re.sub(r'KN\s*OW\s*YO\s*UR\s*CUS\s*TOMER', 'KNOW YOUR CUSTOMER', text, flags=re.IGNORECASE)
    text = re.sub(r'KYC\s*APP\s*LICATION\s*FORM', 'KYC APPLICATION FORM', text, flags=re.IGNORECASE)
    text = re.sub(r'PER\s*SONAL\s*DE\s*TAILS', 'PERSONAL DETAILS', text, flags=re.IGNORECASE)
    text = re.sub(r'ID\s*ENTITY\s*AND\s*ADD\s*RESS', 'IDENTITY AND ADDRESS', text, flags=re.IGNORECASE)
    text = re.sub(r'CURR\s*ENT\s*ADD\s*RESS\s*DE\s*TAILS', 'CURRENT ADDRESS DETAILS', text, flags=re.IGNORECASE)
    text = re.sub(r'E[\s\-]*KYC\s*AUTH\s*ENTICATION', 'E-KYC AUTHENTICATION', text, flags=re.IGNORECASE)
    text = re.sub(r'CER\s*SAI', 'CERSAI', text, flags=re.IGNORECASE)
    
    return text


def has_cashless_request_indicator(text):
    """
    Detects 'REQUEST FOR CASHLESS HOSPITALISATION/HOSPITALIZATION' patterns
    even when OCR introduces spaces, hyphens, or line breaks within words.
    """
    if not text:
        return False

    lowercase_text = text.lower()
    # Quick check using regex allowing arbitrary whitespace/hyphens between words
    if re.search(r'request\s*for\s*cash[\s-]*less\s*hospitali[sz]ation', lowercase_text, re.IGNORECASE):
        return True

    # Fallback: remove whitespace and hyphens to catch heavily distorted OCR output
    compact_text = re.sub(r'[\s\-]+', '', lowercase_text)
    if ('requestforcashlesshospitalisation' in compact_text or
            'requestforcashlesshospitalization' in compact_text):
        return True

    return False


def has_document_header(page_text):
    """
    Detect if a page has a clear document header/title.
    Returns the category if a header is found, None otherwise.
    """
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return None
    
    processed_text = preprocess_text_for_header_detection(page_text)
    text_lower = processed_text.lower()
    header = text_lower[:800]  # Check first 800 chars for headers (increased from 500)
    
    # Check for explicit document type headers (in priority order)
    header_patterns = [
        (r'\bpre[\s\-]*approval\s*certificate\b', "Pre-Auth form C"),
        (r'\bpre[\s\-]*auth\b', "Pre-Auth form C"),
        (r'\bpre[\s\-]*authorization\b', "Pre-Auth form C"),
        (r'\brequest\s*for\s*cash[\s-]*less\s*hospitali[sz]ation\b', "Pre-Auth form C"),
        (r'\bclaim\s*form\b', "Claim Form"),
        (r'\bdischarge\s*summary\b', "Discharge Summary"),
        (r'\bcentral\s*kyc\s*registry\b', "KYC"),
        (r'\bcersai\b', "KYC"),
        (r'\bkyc\s*application\s*form\b', "KYC"),
        (r'\bknow\s*your\s*customer\b', "KYC"),
        (r'\bfinal\s*bill\b', "Hospital Bills"),
        (r'\bhospital.*bill\b', "Hospital Bills"),
        (r'\btest\s*report\b', "Reports"),
        (r'\blab(oratory)?\s*report\b', "Reports"),
        (r'\bpharmacy\b', "Pharmacy Bills"),
    ]
    
    for pattern, category in header_patterns:
        if re.search(pattern, header, re.IGNORECASE):
            return category
    
    # Also check for "CLAIM NO" which is a strong indicator
    if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
        return "Claim Form"
    
    return None


def is_likely_continuation_page(page_text, prev_category):
    """
    Determine if a page is likely a continuation of the previous document.
    A continuation page typically:
    - Lacks a clear document header
    - Has content consistent with the previous page's category
    - Doesn't have conflicting indicators for a different category
    """
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return False
    
    # If this page has a clear header for a different category, it's not a continuation
    page_header_category = has_document_header(page_text)
    if page_header_category and page_header_category != prev_category:
        return False
    
    # Check for STRONG conflicting indicators (be more lenient)
    # Only reject if there are very strong conflicting indicators
    if has_conflicting_indicators(page_text, prev_category):
        # Double-check: if the conflicting indicator is weak, still allow continuation
        processed_text = preprocess_text_for_header_detection(page_text)
        text_lower = processed_text.lower()
        header = text_lower[:500]
        
        # Strong conflicting indicators that should definitely prevent continuation
        strong_conflicts = {
            "Claim Form": [
                r'\bdischarge\s*summary\b',
                r'\bfinal\s*bill\b'
            ],
            "Discharge Summary": [
                r'\bclaim\s*form\b',
                r'\bfinal\s*bill\b'
            ],
            "Hospital Bills": [
                r'\bclaim\s*form\b',
                r'\bdischarge\s*summary\b'
            ]
        }
        
        if prev_category in strong_conflicts:
            for pattern in strong_conflicts[prev_category]:
                if re.search(pattern, header, re.IGNORECASE):
                    return False  # Strong conflict, not a continuation
    
    # Check if page has very little text (might be blank/separator)
    if len(page_text.strip()) < 50:
        return True  # Likely continuation if very little content
    
    # Check if content is consistent with previous category
    processed_text = preprocess_text_for_header_detection(page_text)
    text_lower = processed_text.lower()
    
    # Category-specific continuation indicators
    continuation_indicators = {
        "Claim Form": [
            r'\b(policy|insured|patient|claim|reimbursement|tpa|insurance)\b',
            r'\b(name|address|phone|email|bank|account)\b',
            r'\b(date\s*of\s*admission|date\s*of\s*discharge)\b',
            r'\b(signature|declaration|i\s*hereby)\b',
            r'\b(total\s*amount|amount\s*claimed)\b'
        ],
        "Discharge Summary": [
            r'\b(diagnosis|treatment|medication|follow\s*up|clinical)\b',
            r'\b(admission|discharge|condition|advice)\b',
            r'\b(tab|capsule|syrup|injection|ointment)\b',
            r'\b(patient\s*name|age|sex|consultant)\b'
        ],
        "Hospital Bills": [
            r'\b(bill|charge|amount|gst|tax|invoice)\b',
            r'\b(room|bed|consultation|procedure|service)\b',
            r'\b(item\s*code|rate|quantity|total)\b',
            r'\b(patient\s*name|bill\s*no|bill\s*date)\b'
        ],
        "Pre-Auth form C": [
            r'\b(proposed|estimated|authorized|pre[\s\-]*auth)\b',
            r'\b(treatment|hospitalization|expenses)\b',
            r'\b(to\s*be\s*filled|insured|policy)\b'
        ],
        "Reports": [
            r'\b(test|result|reference\s*range|units?)\b',
            r'\b(lab|diagnostic|specimen|reporting)\b',
            r'\b(mg/dl|mmol/l|normal|abnormal)\b'
        ],
        "KYC": [
            r'\b(personal\s*details|identity|address|proof)\b',
            r'\b(photograph|signature|customer|applicant)\b',
            r'\b(pan|aadhaar|passport|voter)\b'
        ]
    }
    
    if prev_category in continuation_indicators:
        patterns = continuation_indicators[prev_category]
        matches = sum(1 for pattern in patterns if re.search(pattern, text_lower, re.IGNORECASE))
        # If at least one indicator matches, likely continuation
        if matches > 0:
            return True
    
    # More lenient: if no strong conflicting header and page doesn't have its own header,
    # and we're in a sequence, allow continuation
    if not page_header_category:
        # No header on this page - more likely to be continuation if no strong conflicts
        return True
    
    return False

def check_keywords(text):
    """Check for category-specific keywords in the text and return the most likely category."""
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    text_lower = processed_text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}

    # Boost scores for specific document headers
    header = text_lower[:500]  # Check first 500 chars for headers
    
    # Special case for Pre-Auth forms - they should be prioritized even if they contain claim numbers
    cashless_request_header = has_cashless_request_indicator(header)
    
    if (cashless_request_header or
        re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
        re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or
        re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE) or
        re.search(r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b', header, re.IGNORECASE)):
        category_scores["Pre-Auth form C"] += 10
        return "Pre-Auth form C"  # Prioritize pre-auth form when pre-auth indicators are present
    
    # Check for explicit claim form indicators - highest priority
    if re.search(r'\bclaim\s*form\b', header, re.IGNORECASE):
        category_scores["Claim Form"] += 10
        return "Claim Form"  # Immediate return for explicit claim form header
    
    # Check for "Claim No" indicator - highest priority for claim forms
    if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
        category_scores["Claim Form"] += 10
        return "Claim Form"  # Immediate return for claim number presence
    
    # Check for explicit discharge summary indicators - highest priority
    if "discharge summary" in header:
        category_scores["Discharge Summary"] += 10
        return "Discharge Summary"  # Immediate return for explicit discharge summary header
    
    # Check for explicit KYC indicators - highest priority
    if re.search(r'\bcentral\s*kyc\s*registry\b', header, re.IGNORECASE) or re.search(r'\bcersai\b', header, re.IGNORECASE) or re.search(r'\bkyc\s*application\s*form\b', header, re.IGNORECASE) or re.search(r'\bknow\s*your\s*customer\b', header, re.IGNORECASE):
        category_scores["KYC"] += 10
        return "KYC"  # Immediate return for explicit KYC header
    
    # Check for explicit pre-authorization indicators - high priority
    if cashless_request_header or re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE) or re.search(r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b', header, re.IGNORECASE):
        category_scores["Pre-Auth form C"] += 10
        return "Pre-Auth form C"  # Immediate return for explicit pre-auth header
    
    # Check for explicit test report indicators in header - high priority
    if re.search(r'\btest\s*report\b', header, re.IGNORECASE) or re.search(r'\blab(oratory)?\s*report\b', header, re.IGNORECASE) or re.search(r'\bdiagnostics?\b', header, re.IGNORECASE):
        category_scores["Reports"] += 8
        # Continue checking other indicators
    
    # Check for explicit hospital bill indicators in header - high priority
    if "final bill" in header or re.search(r'\bhospital.*bill\b', header, re.IGNORECASE) or re.search(r'\bfinal.*bill\b', header, re.IGNORECASE):
        # Make sure it's not a pre-auth form with "hospital" in the header
        if not (re.search(r'\brequest\s*for\s*cashless\s*hospitali[sz]ation\b', header, re.IGNORECASE) or 
                re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE)):
            category_scores["Hospital Bills"] += 8
        # Don't return immediately, continue checking other indicators
    
    # Check for explicit pharmacy mentions in header - high priority
    if re.search(r'\bpharmacy\b', header, re.IGNORECASE):
        category_scores["Pharmacy Bills"] += 8  # Increased priority for explicit pharmacy mention
        # Don't return immediately, continue checking other indicators
    
    # Check for explicit claim number references - high priority for claim forms
    if re.search(r'\bclaim\s*no[.:]?\b', header, re.IGNORECASE) or re.search(r'\bclaim\s*number\b', header, re.IGNORECASE) or re.search(r'\bref\s*no[.:]?\s*/\s*claim\s*no[.:]?\b', header, re.IGNORECASE):
        category_scores["Claim Form"] += 8
        # Don't return immediately, continue checking other indicators
    
    if "claim form" in header:
        category_scores["Claim Form"] += 5
    elif re.search(r'\bdischarge\b', header, re.IGNORECASE) and not re.search(r'\bbill\b', header, re.IGNORECASE):
        category_scores["Discharge Summary"] += 5
    elif "report" in header or "laboratory" in header or "test" in header or "diagnostics" in header:
        category_scores["Reports"] += 5
    elif "pharmacy" in header or "medical store" in header or "chemist" in header or "drugstore" in header:
        category_scores["Pharmacy Bills"] += 5
    elif "invoice" in header or "bill" in header:
        # Check if it's specifically a pharmacy bill
        if any(term in header for term in ["pharmacy", "medicine", "drug", "prescription"]):
            category_scores["Pharmacy Bills"] += 5
        else:
            category_scores["Hospital Bills"] += 4
    elif "cancelled cheque" in header or "cheque" in header:
        category_scores["Cancelled cheque"] += 5
    elif "diagnostic" in header:
        category_scores["Diagnostic Bills"] += 5
    
    # Add specific pattern detection for claim forms
    claim_form_patterns = [
        r'\bclaim\s*form\b',
        r'\binsurance\s*claim\b',
        r'\bmedical\s*claim\b',
        r'\bhealth\s*claim\b',
        r'\bclaim\s*for\s*reimbursement\b',
        r'\bpatient\s*details\b.*\bpolicy\s*details\b',
        r'\bclaim\s*no[.:]?\b',  # Added pattern for claim number
        r'\bclaim\s*number\b'    # Added pattern for claim number
    ]
    
    claim_form_matches = sum(1 for pattern in claim_form_patterns if re.search(pattern, text_lower))
    if claim_form_matches >= 1:
        category_scores["Claim Form"] += 6
    
    # Check for specific claim form content
    if (re.search(r'\bpolicy\s*(no|number)\b', text_lower) and 
        re.search(r'\binsured\s*person\b', text_lower)) or (
        re.search(r'\bpolicy\s*(no|number)\b', text_lower) and 
        re.search(r'\bclaim\b', text_lower)):
        category_scores["Claim Form"] += 4
    
    # Additional check for claim form specific patterns
    if (re.search(r'\btotal\s*amount\s*claimed\b', text_lower) or
        re.search(r'\bclaim\s*amount\b', text_lower) or
        re.search(r'\breimbursement\b', text_lower) or
        re.search(r'\bsignature\s*of\s*(the|)\s*insured\b', text_lower) or
        re.search(r'\bi\s*hereby\s*declare\b', text_lower)):
        category_scores["Claim Form"] += 5
        
    # Check for claim form vs pre-auth differentiation
    # Claim forms typically deal with PAST events, pre-auth with FUTURE events
    if re.search(r'\b(incurred|spent|paid|underwent|hospitalized|treated)\b', text_lower):
        category_scores["Claim Form"] += 3
        category_scores["Pre-Auth form C"] -= 2  # Reduce pre-auth score
    
    # Pre-auth specific terms indicating future treatment
    if re.search(r'\b(proposed|planned|estimated|expected|upcoming|scheduled)\s*(treatment|procedure|hospitalization|surgery)\b', text_lower) or re.search(r'\bto\s*be\s*filled\s*by\s*insured\s*patient\b', text_lower):
        category_scores["Pre-Auth form C"] += 5  # Increased score
        category_scores["Claim Form"] -= 2  # Reduce claim form score
        category_scores["Hospital Bills"] -= 3  # Reduce hospital bill score
    
    # Add specific pattern detection for pre-authorization forms
    preauth_patterns = [
        r'\bpre[\s\-]*approval\b',
        r'\bpre[\s\-]*auth\b',
        r'\bpre[\s\-]*authorization\b',
        r'\bauthorization\s*certificate\b',
        r'\bapproval\s*certificate\b',
        r'\brequest\s*for\s*cash[\s\-]*less\b',
        r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b',
        r'\bdetails\s*of\s*the\s*third\s*party\s*administrator\b',
        r'\bto\s*be\s*filled\s*by\s*insured\s*patient\b'
    ]
    
    preauth_matches = sum(1 for pattern in preauth_patterns if re.search(pattern, text_lower))
    if preauth_matches >= 1:
        category_scores["Pre-Auth form C"] += 6
    
    # Check for specific pre-authorization content
    if (re.search(r'\bestimated\s*expenses\b', text_lower) or 
        re.search(r'\bproposed\s*treatment\b', text_lower) or 
        re.search(r'\bauthorized\s*limit\b', text_lower) or
        re.search(r'\binsured\s*card\s*id\s*number\b', text_lower) or
        re.search(r'\bpolicy\s*number\s*or\s*name\s*of\s*corporate\b', text_lower) or
        re.search(r'\bfamily\s*physician\b', text_lower)) and not re.search(r'\bfinal\s*bill\b', text_lower):
        category_scores["Pre-Auth form C"] += 6  # Increased score
        category_scores["Hospital Bills"] -= 4  # Reduce hospital bill score
        
    # Check for KYC document patterns
    kyc_patterns = [
        r'\bcentral\s*kyc\s*registry\b',
        r'\bcersai\b',
        r'\bkyc\s*application\s*form\b',
        r'\bknow\s*your\s*customer\b',
        r'\bpersonal\s*details\b',
        r'\bidentity\s*and\s*address\b',
        r'\bcurrent\s*address\s*details\b',
        r'\bproof\s*of\s*identity\b',
        r'\bproof\s*of\s*address\b',
        r'\be[\s\-]*kyc\s*authentication\b',
        r'\bvideo\s*kyc\b',
        r'\bphoto\b'
    ]
    
    kyc_matches = sum(1 for pattern in kyc_patterns if re.search(pattern, text_lower))
    if kyc_matches >= 1:
        category_scores["KYC"] += 8  # High priority for KYC documents
        
    # Check for specific KYC content
    if (re.search(r'\bapplication\s*form\b', text_lower) and 
        (re.search(r'\bkyc\b', text_lower) or re.search(r'\bcustomer\b', text_lower))) or (
        re.search(r'\bpersonal\s*details\b', text_lower) and 
        re.search(r'\baddress\s*details\b', text_lower)):
        category_scores["KYC"] += 6
    
    # Look for specific discharge summary patterns
    discharge_patterns = [
        r'\bdischarge\s*summary\b',
        r'\bdischarge\s*note\b',
        r'\bcondition\s*(on|at)\s*discharge\b',
        r'\btreatment\s*given\s*in\s*hospital\b',
        r'\bdate\s*of\s*admission.*date\s*of\s*discharge\b',
        r'\bdiagnosis\b.*\btreatment\b'
    ]
    
    discharge_matches = sum(1 for pattern in discharge_patterns if re.search(pattern, text_lower))
    if discharge_matches >= 2:
        category_scores["Discharge Summary"] += 6
    
    # Check for discharge summary specific content
    if re.search(r'\b(admission date|discharge date)\b', text_lower) and re.search(r'\b(diagnosis|treatment|clinical summary)\b', text_lower):
        category_scores["Discharge Summary"] += 4
    
    # Check for laboratory report specific patterns
    lab_report_patterns = [
        r'\b(test|laboratory)\s*report\b',
        r'\b(reference|normal)\s*range\b',
        r'\b(biological|reference)\s*interval\b',
        r'\bresults?\b.*\bunits?\b',
        r'\bspecimen\b.*\b(collected|drawn|received)\b',
        r'\b(test|parameter)s?\b.*\bresults?\b'
    ]
    
    lab_report_matches = sum(1 for pattern in lab_report_patterns if re.search(pattern, text_lower))
    if lab_report_matches >= 2:
        category_scores["Reports"] += 6
    
    # Check for specific laboratory test mentions
    if re.search(r'\b(glucose|cholesterol|triglycerides|hdl|ldl|hemoglobin|wbc|rbc|platelets|creatinine|urea|bilirubin|sgpt|sgot)\b', text_lower):
        category_scores["Reports"] += 4
    
    # Check for measurement units common in lab reports
    if re.search(r'\b(mg\/dl|mmol\/l|g\/dl|u\/l|cells\/mm3|%)\b', text_lower) and not re.search(r'\bprice|cost|charge|amount\b', text_lower):
        category_scores["Reports"] += 3
    
    # Check for hospital-specific service items
    hospital_service_count = len(re.findall(r'\b(bed charges|room charges|doctor consultancy|pathological investigation|cardiological investigation|icu charges|operation theatre|surgery|procedure|admission|discharge)\b', text_lower))
    if hospital_service_count >= 2:
        # Make sure it's not a pre-auth form with estimated charges
        if not (re.search(r'\brequest\s*for\s*cashless\b', text_lower) or 
                re.search(r'\bto\s*be\s*filled\s*by\s*insured\b', text_lower) or
                re.search(r'\bpre[\s\-]*auth\b', text_lower)):
            category_scores["Hospital Bills"] += 5
        
    # Special patterns for cancelled cheques
    if re.search(r'\b(ifsc|micr)\b.*?code', text_lower) or re.search(r'\baccount\b.*?\bnumber\b', text_lower):
        category_scores["Cancelled cheque"] += 3
        
    if "cheque" in text_lower and ("cancel" in text_lower or "cancelled" in text_lower):
        category_scores["Cancelled cheque"] += 4
    
    # Special patterns for pharmacy bills
    medicine_count = len(re.findall(r'\b(tablet|capsule|syrup|injection|ointment|ml|mg|dose|dosage)\b', text_lower))
    if medicine_count >= 3:
        category_scores["Pharmacy Bills"] += 3
    
    # Check for common pharmacy medications
    if any(med in text_lower for med in ["tablet", "capsule", "syrup", "injection", "ointment"]):
        category_scores["Pharmacy Bills"] += 2
    
    # Check for pharmacy-specific identifiers
    if re.search(r'\b(pharmacy|chemist|medical store|drugstore)\b', text_lower):
        category_scores["Pharmacy Bills"] += 3
    
    if re.search(r'\b(prescription|rx|prescribed|refill)\b', text_lower):
        category_scores["Pharmacy Bills"] += 2

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


def categorize_document_with_gemini(text):
    """Categorize the document using Gemini API."""
    if not gemini_client:
        return {'category': "Gemini API not available", 'confidence': 0.0}
    
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    # First, try keyword-based classification with confidence
    keyword_result = check_keywords_with_confidence(processed_text)
    if keyword_result['category'] and keyword_result['confidence'] >= 0.8:
        return keyword_result

    # Fallback to Gemini if keyword check is inconclusive
    prompt = get_document_classification_prompt(processed_text)

    try:
        response = gemini_client.generate_content(prompt)
        category = response.text.strip()

        # Ensure the response is one of the valid categories
        valid_categories = ["Claim Form", "Discharge Summary", "Reports", 
                          "Cancelled cheque", "Hospital Bills", "Pharmacy Bills", 
                          "Diagnostic Bills", "KYC", "Pre-Auth form C", "Others"]
        for valid_cat in valid_categories:
            if valid_cat.lower() in category.lower():
                return {'category': valid_cat, 'confidence': 0.7}  # Gemini confidence

        return {'category': "Others", 'confidence': 0.5}  # Default
    except Exception as e:
        return {'category': f"Error during Gemini categorization: {str(e)}", 'confidence': 0.0}


def categorize_document_with_confidence(text, api_provider="openai"):
    """Categorize the document with confidence scoring using specified API provider."""
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    # First, try keyword-based classification with confidence
    keyword_result = check_keywords_with_confidence(processed_text)
    if keyword_result['category'] and keyword_result['confidence'] >= 0.8:
        return keyword_result

    # Choose API provider for LLM fallback
    if api_provider.lower() == "gemini" and gemini_client:
        return categorize_document_with_gemini(text)
    elif api_provider.lower() == "openai" and openai_client:
        return categorize_document_with_openai(text)
    else:
        # Fallback to available API
        if gemini_client:
            return categorize_document_with_gemini(text)
        elif openai_client:
            return categorize_document_with_openai(text)
        else:
            return {'category': "No API available", 'confidence': 0.0}


def categorize_document_with_openai(text):
    """Categorize the document using OpenAI API."""
    if not openai_client:
        return {'category': "OpenAI API not available", 'confidence': 0.0}
    
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    # First, try keyword-based classification with confidence
    keyword_result = check_keywords_with_confidence(processed_text)
    if keyword_result['category'] and keyword_result['confidence'] >= 0.8:
        return keyword_result

    # Fallback to OpenAI if keyword check is inconclusive
    prompt = get_document_classification_prompt(processed_text)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": get_openai_system_message()},
                {"role": "user", "content": prompt}
            ]
        )
        category = response.choices[0].message.content.strip()

        # Ensure the response is one of the valid categories
        valid_categories = ["Claim Form", "Discharge Summary", "Reports", 
                          "Cancelled cheque", "Hospital Bills", "Pharmacy Bills", 
                          "Diagnostic Bills", "KYC", "Pre-Auth form C", "Others"]
        for valid_cat in valid_categories:
            if valid_cat.lower() in category.lower():
                return {'category': valid_cat, 'confidence': 0.7}  # OpenAI confidence

        return {'category': "Others", 'confidence': 0.5}  # Default
    except Exception as e:
        return {'category': f"Error during OpenAI categorization: {str(e)}", 'confidence': 0.0}


def check_keywords_with_confidence(text):
    """Check for category-specific keywords with confidence scoring."""
    processed_text = preprocess_text_for_header_detection(text)
    text_lower = processed_text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}
    
    # Header analysis (first 500 characters) - highest confidence
    header = text_lower[:500]
    cashless_request_header = has_cashless_request_indicator(header)
    
    # Strong header indicators (confidence 0.9-1.0)
    if re.search(r'\bclaim\s*form\b', header, re.IGNORECASE):
        return {'category': "Claim Form", 'confidence': 1.0}
    
    # Check for "Claim No" indicator - highest priority for claim forms
    if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
        return {'category': "Claim Form", 'confidence': 1.0}
    
    if "discharge summary" in header:
        return {'category': "Discharge Summary", 'confidence': 1.0}
    
    if re.search(r'\bcentral\s*kyc\s*registry\b', header, re.IGNORECASE) or re.search(r'\bcersai\b', header, re.IGNORECASE):
        return {'category': "KYC", 'confidence': 1.0}
    
    if (cashless_request_header or
        re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
        re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or
        re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE) or
        re.search(r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b', header, re.IGNORECASE)):
        return {'category': "Pre-Auth form C", 'confidence': 1.0}
    
    if "final bill" in header or re.search(r'\bhospital.*bill\b', header, re.IGNORECASE):
        return {'category': "Hospital Bills", 'confidence': 0.9}
    
    if re.search(r'\btest\s*report\b', header, re.IGNORECASE) or re.search(r'\blab(oratory)?\s*report\b', header, re.IGNORECASE):
        return {'category': "Reports", 'confidence': 0.9}
    
    if re.search(r'\bpharmacy\b', header, re.IGNORECASE):
        return {'category': "Pharmacy Bills", 'confidence': 0.9}
    
    # Medium confidence indicators (0.7-0.8)
    if re.search(r'\bclaim\s*no[.:]?\b', header, re.IGNORECASE) or re.search(r'\bclaim\s*number\b', header, re.IGNORECASE):
        category_scores["Claim Form"] += 8
    
    if re.search(r'\bdischarge\b', header, re.IGNORECASE) and not re.search(r'\bbill\b', header, re.IGNORECASE):
        category_scores["Discharge Summary"] += 6
    
    # Count keyword matches for each category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                category_scores[category] += 1
    
    # Find the category with the most matches
    max_score = max(category_scores.values())
    if max_score >= 3:  # Require at least 3 keyword matches for good confidence
        for category, score in category_scores.items():
            if score == max_score:
                confidence = min(0.8, 0.5 + (score * 0.05))  # Scale confidence based on score
                return {'category': category, 'confidence': confidence}
    
    return {'category': None, 'confidence': 0.0}


def categorize_document(text):
    """Legacy function for backward compatibility."""
    result = categorize_document_with_confidence(text)
    return result['category'] if result['category'] else "Others"


def format_output_compact(page_categories):
    """
    Format page categories into compact output format: Category1 (start–end), Category2 (start–end), ...
    
    Args:
        page_categories: List of category strings for each page (1-indexed pages)
    
    Returns:
        Formatted string like "Claim Form (1–5), Discharge Summary (6–7), Hospital Bill (8–15)"
    """
    if not page_categories:
        return ""
    
    # Category name mapping for output display
    category_display_map = {
        "Hospital Bills": "Hospital Bill",
        "Pharmacy Bills": "Pharmacy Bill",
        "Diagnostic Bills": "Diagnostic Bill"
    }
    
    # Group consecutive pages with the same category
    grouped = []
    current_category = page_categories[0]
    start_page = 1
    end_page = 1
    
    for i in range(1, len(page_categories)):
        if page_categories[i] == current_category:
            end_page = i + 1
        else:
            # Add the current group
            grouped.append((current_category, start_page, end_page))
            
            # Start new group
            current_category = page_categories[i]
            start_page = i + 1
            end_page = i + 1
    
    # Add the last group
    grouped.append((current_category, start_page, end_page))
    
    # Format the output
    formatted_parts = []
    for category, start, end in grouped:
        # Map category name for display
        display_category = category_display_map.get(category, category)
        
        # Format: Category (start–end) or Category (start) for single page
        if start == end:
            formatted_parts.append(f"{display_category} ({start})")
        else:
            formatted_parts.append(f"{display_category} ({start}–{end})")
    
    return ", ".join(formatted_parts)


def detect_ambiguous_preauth_claim(page_text):
    """
    Detect if a page could be either Pre-Auth form C or Claim Form.
    Returns True if ambiguous, False otherwise.
    """
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return False
    
    processed_text = preprocess_text_for_header_detection(page_text)
    text_lower = processed_text.lower()
    header = text_lower[:500]
    
    # Check for both Pre-Auth and Claim Form indicators
    has_preauth_indicators = (
        has_cashless_request_indicator(header) or
        re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or
        re.search(r'\bpre[\s\-]*approval\b', header, re.IGNORECASE) or
        re.search(r'\bproposed\s*(treatment|date|hospitalization)\b', text_lower, re.IGNORECASE) or
        re.search(r'\bestimated\s*(expenses|cost)\b', text_lower, re.IGNORECASE) or
        re.search(r'\bto\s*be\s*filled\s*by\s*insured\b', text_lower, re.IGNORECASE)
    )
    
    has_claim_indicators = (
        re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE) or
        re.search(r'\bclaim\s*form\b', text_lower, re.IGNORECASE) or
        re.search(r'\bclaim\s*number\b', text_lower, re.IGNORECASE) or
        re.search(r'\btotal\s*amount\s*claimed\b', text_lower, re.IGNORECASE) or
        re.search(r'\breimbursement\b', text_lower, re.IGNORECASE)
    )
    
    # If both indicators are present and neither is clearly dominant, it's ambiguous
    if has_preauth_indicators and has_claim_indicators:
        # Check if one is clearly dominant
        strong_preauth = (
            has_cashless_request_indicator(header) or
            re.search(r'\brequest\s*for\s*cashless\s*hospitali[sz]ation\b', text_lower, re.IGNORECASE)
        )
        strong_claim = re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE)
        
        # If neither is clearly dominant, it's ambiguous
        if not (strong_preauth or strong_claim):
            return True
    
    return False


def post_process_categorization(page_results):
    """
    Post-process categorization results to verify and improve accuracy.
    This function performs validation checks and corrections.
    
    Args:
        page_results: List of dicts with 'category', 'confidence', 'page_num', 'page_text'
    
    Returns:
        List of corrected page_results
    """
    corrected_results = []
    
    for i, result in enumerate(page_results):
        category = result['category']
        confidence = result['confidence']
        page_text = result.get('page_text', '')
        page_num = result.get('page_num', i + 1)
        
        # Skip processing if error in text extraction
        if page_text.startswith("Error") or "No text could be extracted" in page_text:
            corrected_results.append(result)
            continue
        
        # Post-processing rules
        processed_text = preprocess_text_for_header_detection(page_text)
        text_lower = processed_text.lower()
        header = text_lower[:500]
        
        # Rule 1: Verify Pre-Auth vs Claim Form distinction
        # Pre-Auth forms should have future-oriented language
        # Claim Forms should have past-oriented language
        if category in ["Pre-Auth form C", "Claim Form"]:
            has_future_language = any(term in text_lower for term in [
                "proposed", "planned", "estimated", "expected", "to be filled",
                "request for cashless", "pre-authorization", "pre-approval"
            ])
            has_past_language = any(term in text_lower for term in [
                "incurred", "spent", "paid", "underwent", "hospitalized", "treated",
                "claim no", "claim number", "reimbursement"
            ])
            
            # Check if page is ambiguous
            is_ambiguous = detect_ambiguous_preauth_claim(page_text)
            
            # If Pre-Auth but has strong claim indicators, reconsider
            if category == "Pre-Auth form C" and has_past_language and not has_future_language:
                if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
                    category = "Claim Form"
                    confidence = min(0.9, confidence + 0.1)
            
            # If Claim Form but has strong pre-auth indicators, reconsider
            if category == "Claim Form" and has_future_language and not has_past_language:
                if has_cashless_request_indicator(header) or re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE):
                    category = "Pre-Auth form C"
                    confidence = min(0.9, confidence + 0.1)
        
        # Rule 2: Verify Hospital Bills vs Discharge Summary
        # Hospital Bills should have billing/charges information
        # Discharge Summary should have clinical information
        if category in ["Hospital Bills", "Discharge Summary"]:
            has_billing_info = any(term in text_lower for term in [
                "bill no", "bill number", "total amount", "charges", "gst", "invoice",
                "item code", "rate", "amount", "sgst", "cgst", "tax"
            ])
            has_clinical_info = any(term in text_lower for term in [
                "diagnosis", "treatment", "admission date", "discharge date",
                "clinical summary", "follow up", "medication", "procedure"
            ])
            
            if category == "Discharge Summary" and has_billing_info and not has_clinical_info:
                # Check if it's actually a hospital bill
                if "final bill" in text_lower or "hospital" in text_lower:
                    category = "Hospital Bills"
                    confidence = min(0.9, confidence + 0.1)
            
            if category == "Hospital Bills" and has_clinical_info and not has_billing_info:
                # Check if it's actually a discharge summary
                if "discharge summary" in text_lower:
                    category = "Discharge Summary"
                    confidence = min(0.9, confidence + 0.1)
        
        # Rule 3: Verify Reports vs Bills
        # Reports should have test results without prices
        # Bills should have prices/charges
        if category in ["Reports", "Hospital Bills", "Diagnostic Bills"]:
            has_test_results = any(term in text_lower for term in [
                "test report", "lab report", "reference range", "normal range",
                "results", "units", "mg/dl", "mmol/l"
            ])
            has_prices = any(term in text_lower for term in [
                "price", "cost", "charge", "amount", "rate", "total"
            ])
            
            if category == "Reports" and has_prices and not has_test_results:
                # Might be a diagnostic bill
                if "diagnostic" in text_lower:
                    category = "Diagnostic Bills"
                    confidence = min(0.9, confidence + 0.1)
                elif "hospital" in text_lower:
                    category = "Hospital Bills"
                    confidence = min(0.9, confidence + 0.1)
        
        # Rule 4: Context-based validation
        # Check if category makes sense given surrounding pages
        if i > 0 and i < len(page_results) - 1:
            prev_category = corrected_results[-1]['category'] if corrected_results else page_results[i-1]['category']
            next_category = page_results[i+1]['category'] if i+1 < len(page_results) else None
            
            # If current page is isolated (different from both neighbors), verify it
            if prev_category != category and (next_category is None or next_category != category):
                # Double-check with explicit indicators
                explicit_category = check_explicit_document_indicators(page_text, category, confidence)
                if explicit_category and explicit_category != category:
                    category = explicit_category
                    confidence = min(0.9, confidence + 0.1)
        
        # Update result
        corrected_result = result.copy()
        corrected_result['category'] = category
        corrected_result['confidence'] = confidence
        corrected_results.append(corrected_result)
    
    return corrected_results


def categorize_multi_page_document(page_texts, api_provider="openai"):
    """Categorize each page of a multi-page document with context-aware continuity."""
    page_results = []
    
    # First pass: categorize each page with confidence
    for i, page_text in enumerate(page_texts):
        if page_text.startswith("Error") or "No text could be extracted" in page_text:
            page_results.append({'category': "Others", 'confidence': 0.0, 'page_num': i+1, 'page_text': page_text})
        else:
            result = categorize_document_with_confidence(page_text, api_provider)
            result['page_num'] = i + 1
            result['page_text'] = page_text  # Store the page text for better analysis
            page_results.append(result)
    
    # Second pass: analyze document structure for patterns
    page_results = analyze_document_structure(page_results)
    
    # Third pass: apply context-aware continuity logic with improved boundary detection
    page_categories = apply_document_continuity_improved(page_results)
    
    # Fourth pass: post-process to verify and improve categorization
    # Update page_results with final categories for post-processing
    for i, category in enumerate(page_categories):
        page_results[i]['category'] = category
    
    page_results = post_process_categorization(page_results)
    
    # Extract final categories after post-processing
    final_page_categories = [r['category'] for r in page_results]
    
    # Fifth pass: Apply final smoothing to merge small isolated groups
    final_page_categories = apply_final_smoothing(final_page_categories, page_results)
    
    # Sixth pass: Apply aggressive merging for better grouping
    final_page_categories = apply_aggressive_merging(final_page_categories, page_results)
    
    # Seventh pass: Pattern-based correction for common misclassification patterns
    final_page_categories = apply_pattern_based_correction(final_page_categories, page_results)
    
    # Eighth pass: Final structure-based correction using majority voting in regions
    final_page_categories = apply_structure_based_correction(final_page_categories, page_results)
    
    # Ninth pass: Final Pre-Auth form C extension check - ensure page 4 is Pre-Auth form C if pages 1-3 are
    final_page_categories = ensure_preauth_continuation(final_page_categories, page_results)
    
    # Tenth pass: Final Claim Form extension check - ensure page 5 is Claim Form if pages 1-4 are
    final_page_categories = ensure_claim_form_continuation(final_page_categories, page_results)
    
    # Group consecutive pages with the same category (for detailed display)
    grouped_results = []
    current_category = final_page_categories[0]
    start_page = 1
    end_page = 1
    
    for i in range(1, len(final_page_categories)):
        if final_page_categories[i] == current_category:
            end_page = i + 1
        else:
            # Add the current group
            if start_page == end_page:
                grouped_results.append(f"Page {start_page}: {current_category}")
            else:
                grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
            
            # Start new group
            current_category = final_page_categories[i]
            start_page = i + 1
            end_page = i + 1
    
    # Add the last group
    if start_page == end_page:
        grouped_results.append(f"Page {start_page}: {current_category}")
    else:
        grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
    
    return grouped_results, final_page_categories


def check_explicit_document_indicators(page_text, current_category, confidence):
    """Check for explicit document type indicators that override continuity logic."""
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return current_category
    
    text_lower = page_text.lower()
    header = text_lower[:500]  # Check first 500 chars for headers
    cashless_request_header = has_cashless_request_indicator(header)
    cashless_request_body = has_cashless_request_indicator(page_text)
    
    # Strong header indicators that should override continuity
    if re.search(r'\bclaim\s*form\b', header, re.IGNORECASE):
        return "Claim Form"
    
    # Check for "Claim No" indicator - highest priority for claim forms
    if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
        return "Claim Form"
    
    if "discharge summary" in header:
        return "Discharge Summary"
    
    if re.search(r'\bcentral\s*kyc\s*registry\b', header, re.IGNORECASE) or re.search(r'\bcersai\b', header, re.IGNORECASE):
        return "KYC"
    
    if (cashless_request_header or cashless_request_body or
        re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
        re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or
        re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE) or
        re.search(r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b', header, re.IGNORECASE)):
        return "Pre-Auth form C"
    
    if "final bill" in header or re.search(r'\bhospital.*bill\b', header, re.IGNORECASE):
        return "Hospital Bills"
    
    if re.search(r'\btest\s*report\b', header, re.IGNORECASE) or re.search(r'\blab(oratory)?\s*report\b', header, re.IGNORECASE):
        return "Reports"
    
    if re.search(r'\bpharmacy\b', header, re.IGNORECASE):
        return "Pharmacy Bills"
    
    # Check for strong content indicators that should override continuity
    # Claim form indicators
    if (re.search(r'\bclaim\s*no[.:]?\b', text_lower) and 
        re.search(r'\bpolicy\s*(no|number)\b', text_lower) and
        re.search(r'\binsured\s*person\b', text_lower)):
        return "Claim Form"
    
    # Pre-auth form indicators
    if (re.search(r'\bestimated\s*expenses\b', text_lower) and 
        re.search(r'\bproposed\s*treatment\b', text_lower) and
        re.search(r'\bto\s*be\s*filled\s*by\s*insured\b', text_lower)):
        return "Pre-Auth form C"
    
    # Hospital bill indicators
    if (re.search(r'\bfinal\s*bill\b', text_lower) and 
        re.search(r'\b(bed charges|room charges|doctor consultancy)\b', text_lower)):
        return "Hospital Bills"
    
    # Pharmacy bill indicators
    if (re.search(r'\bpharmacy\b', text_lower) and 
        re.search(r'\b(tablet|capsule|syrup|injection|medicine)\b', text_lower)):
        return "Pharmacy Bills"
    
    # Report indicators
    if (re.search(r'\b(test|laboratory)\s*report\b', text_lower) and 
        re.search(r'\b(reference|normal)\s*range\b', text_lower) and
        not re.search(r'\bprice|cost|charge|amount\b', text_lower)):
        return "Reports"
    
    return current_category


def apply_document_continuity_improved(page_results):
    """Apply improved context-aware continuity logic with better boundary detection."""
    if len(page_results) <= 1:
        return [result['category'] for result in page_results]
    
    # First, identify document boundaries based on high-confidence pages
    document_boundaries = identify_document_boundaries(page_results)
    
    final_categories = []
    
    for i, result in enumerate(page_results):
        category = result['category']
        confidence = result['confidence']
        page_text = result.get('page_text', '')
        
        # Check if this page has a clear document header
        page_header_category = has_document_header(page_text)
        
        # If page has a header, use that category (highest priority)
        if page_header_category:
            final_categories.append(page_header_category)
            continue
        
        # Check if this page has strong indicators for a specific document type
        explicit_category = check_explicit_document_indicators(page_text, category, confidence)
        if explicit_category and explicit_category != category:
            final_categories.append(explicit_category)
            continue
        
        # High confidence results (0.8+) are kept as-is, but check for explicit indicators first
        if confidence >= 0.8:
            final_categories.append(category)
            continue
        
        # NEW: Check if previous page had a header and this page is likely a continuation
        if i > 0:
            prev_page_text = page_results[i-1].get('page_text', '')
            prev_header_category = has_document_header(prev_page_text)
            
            if prev_header_category:
                # Previous page had a header - check if this page is a continuation
                if is_likely_continuation_page(page_text, prev_header_category):
                    final_categories.append(prev_header_category)
                    continue
        
        # Check if we're in a sequence of the same category (even without explicit header)
        # If previous 2-3 pages are the same category and this page doesn't have a conflicting header, continue
        # BUT be careful not to extend Claim Form into Discharge Summary territory
        if i >= 2:
            # Check last 2-3 pages
            recent_categories = [page_results[j]['category'] for j in range(max(0, i-3), i)]
            if len(recent_categories) >= 2:
                # If all recent pages are the same category
                if len(set(recent_categories)) == 1:
                    dominant_category = recent_categories[0]
                    
                    # SPECIAL CASE: Don't extend Claim Form too far - check for Discharge Summary
                    if dominant_category == "Claim Form" and i >= 5:
                        # Check if this page (page 6+) has Discharge Summary indicators
                        processed_text = preprocess_text_for_header_detection(page_text)
                        text_lower = processed_text.lower()
                        header = text_lower[:800]
                        
                        discharge_indicators = [
                            r'\bdischarge\s*summary\b',
                            r'\bdischarge\s*note\b',
                            r'\bcondition\s*(on|at)\s*discharge\b',
                            r'\btreatment\s*given\s*in\s*hospital\b'
                        ]
                        
                        has_discharge = any(re.search(pattern, header, re.IGNORECASE) 
                                          for pattern in discharge_indicators)
                        
                        if has_discharge:
                            # This is Discharge Summary, don't extend Claim Form
                            pass
                        else:
                            # Check if this page has a conflicting header
                            page_header = has_document_header(page_text)
                            if not page_header or page_header == dominant_category:
                                # Check if this page conflicts with the dominant category
                                if not has_conflicting_indicators(page_text, dominant_category):
                                    # Check if it's a reasonable continuation
                                    if is_likely_continuation_page(page_text, dominant_category) or confidence < 0.7:
                                        final_categories.append(dominant_category)
                                        continue
                    else:
                        # For other categories or early pages, use normal logic
                        # Check if this page has a conflicting header
                        page_header = has_document_header(page_text)
                        if not page_header or page_header == dominant_category:
                            # Check if this page conflicts with the dominant category
                            if not has_conflicting_indicators(page_text, dominant_category):
                                # Check if it's a reasonable continuation
                                if is_likely_continuation_page(page_text, dominant_category) or confidence < 0.7:
                                    final_categories.append(dominant_category)
                                    continue
        
        # Check if this page is within a document boundary
        document_type = get_document_type_for_page(i, document_boundaries, page_results)
        if document_type:
            final_categories.append(document_type)
            continue
        
        # Check if we're in a continuation sequence (previous pages had headers)
        # Look back to find the most recent page with a header
        header_category = None
        header_page_idx = None
        for j in range(i-1, max(-1, i-5), -1):  # Look back up to 4 pages
            if j >= 0:
                prev_text = page_results[j].get('page_text', '')
                prev_header = has_document_header(prev_text)
                if prev_header:
                    header_category = prev_header
                    header_page_idx = j
                    break
        
        # If we found a header recently and this page looks like a continuation
        if header_category and header_page_idx is not None:
            # Check if all pages between header and this one are also continuations
            all_continuations = True
            for j in range(header_page_idx + 1, i):
                if j < len(page_results):
                    inter_text = page_results[j].get('page_text', '')
                    if not is_likely_continuation_page(inter_text, header_category):
                        all_continuations = False
                        break
            
            # If this page is also a continuation, use the header category
            if all_continuations and is_likely_continuation_page(page_text, header_category):
                final_categories.append(header_category)
                continue
        
        # For low confidence results, apply continuity logic more aggressively
        if confidence < 0.6:
            # Look for strong indicators in nearby pages (extend search window)
            context_category = find_context_category_extended(page_results, i, window=5)  # Increased window
            if context_category:
                final_categories.append(context_category)
                continue
            
            # If no context found, check previous and next pages
            if i > 0 and i + 1 < len(page_results):
                prev_cat = page_results[i-1]['category']
                next_cat = page_results[i+1]['category']
                
                # If previous and next pages agree, use that category
                if prev_cat == next_cat and page_results[i-1]['confidence'] >= 0.6:
                    if not has_conflicting_indicators(page_text, prev_cat):
                        final_categories.append(prev_cat)
                        continue
                
                # Otherwise, prefer previous page's category if it has decent confidence
                if page_results[i-1]['confidence'] >= 0.6:
                    if not has_conflicting_indicators(page_text, prev_cat):
                        final_categories.append(prev_cat)
                        continue
        
        # Medium confidence results - check for document boundaries and continuity
        if 0.6 <= confidence < 0.8:
            # Check if this might be a continuation of previous document
            if i > 0:
                prev_category = page_results[i-1]['category']
                prev_confidence = page_results[i-1]['confidence']
                
                # If previous page had same category and reasonable confidence, likely continuation
                if prev_category == category or (prev_confidence >= 0.7 and is_likely_continuation(page_results[i-1], result)):
                    final_categories.append(prev_category)
                    continue
                
                # Check if previous page had high confidence, use that category (more aggressive)
                if prev_confidence >= 0.7:  # Lowered threshold from 0.8 to 0.7
                    # Only use previous category if it makes sense (not conflicting explicit indicators)
                    if not has_conflicting_indicators(page_text, prev_category):
                        final_categories.append(prev_category)
                        continue
                
                # Also check next page for context
                if i + 1 < len(page_results):
                    next_category = page_results[i+1]['category']
                    next_confidence = page_results[i+1]['confidence']
                    
                    # If next page has high confidence and matches previous, likely continuation
                    if (next_confidence >= 0.7 and 
                        next_category == prev_category and 
                        not has_conflicting_indicators(page_text, prev_category)):
                        final_categories.append(prev_category)
                        continue
        
        # Default to original category
        final_categories.append(category)
    
    return final_categories


def find_context_category_extended(page_results, current_index, window=3):
    """Find the most likely category based on extended context from nearby pages."""
    # Look at previous and next pages for strong indicators
    context_pages = []
    
    # Check previous pages (extended window)
    for i in range(max(0, current_index - window), current_index):
        if page_results[i]['confidence'] >= 0.7:
            context_pages.append(page_results[i])
    
    # Check next pages (extended window)
    for i in range(current_index + 1, min(len(page_results), current_index + window + 1)):
        if page_results[i]['confidence'] >= 0.7:
            context_pages.append(page_results[i])
    
    if not context_pages:
        return None
    
    # Find the most common high-confidence category in context
    category_counts = {}
    for page in context_pages:
        cat = page['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Return the most frequent category
    if category_counts:
        return max(category_counts, key=category_counts.get)
    
    return None


def has_conflicting_indicators(page_text, category):
    """Check if page text has strong indicators conflicting with the given category."""
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return False
    
    text_lower = page_text.lower()
    header = text_lower[:500]
    
    # Define conflicting indicators for each category
    conflicts = {
        "Claim Form": [
            r'\bdischarge\s*summary\b',
            r'\bfinal\s*bill\b',
            r'\bpre[\s\-]*auth\b',
            r'\brequest\s*for\s*cashless\b'
        ],
        "Discharge Summary": [
            r'\bclaim\s*form\b',
            r'\bclaim\s*no[.:]?\b',
            r'\bfinal\s*bill\b',
            r'\bpre[\s\-]*auth\b'
        ],
        "Hospital Bills": [
            r'\bclaim\s*form\b',
            r'\bdischarge\s*summary\b',
            r'\bpre[\s\-]*auth\b'
        ],
        "Pre-Auth form C": [
            r'\bclaim\s*no[.:]?\b',
            r'\bdischarge\s*summary\b',
            r'\bfinal\s*bill\b'
        ]
    }
    
    if category in conflicts:
        for pattern in conflicts[category]:
            if re.search(pattern, header, re.IGNORECASE):
                return True
    
    return False


def apply_document_continuity(page_results):
    """Apply context-aware continuity logic to improve categorization accuracy."""
    if len(page_results) <= 1:
        return [result['category'] for result in page_results]
    
    # First, identify document boundaries based on high-confidence pages
    document_boundaries = identify_document_boundaries(page_results)
    
    final_categories = []
    
    for i, result in enumerate(page_results):
        category = result['category']
        confidence = result['confidence']
        
        # High confidence results (0.8+) are kept as-is
        if confidence >= 0.8:
            final_categories.append(category)
            continue
        
        # Check if this page is within a document boundary
        document_type = get_document_type_for_page(i, document_boundaries, page_results)
        if document_type:
            final_categories.append(document_type)
            continue
        
        # For low confidence results, apply continuity logic
        if confidence < 0.6:
            # Look for strong indicators in nearby pages
            context_category = find_context_category(page_results, i)
            if context_category:
                final_categories.append(context_category)
                continue
        
        # Medium confidence results - check for document boundaries
        if 0.6 <= confidence < 0.8:
            # Check if this might be a continuation of previous document
            if i > 0 and is_likely_continuation(page_results[i-1], result):
                final_categories.append(page_results[i-1]['category'])
                continue
        
        # Default to original category
        final_categories.append(category)
    
    return final_categories


def identify_document_boundaries(page_results):
    """Identify document boundaries based on high-confidence pages."""
    boundaries = []
    
    for i, result in enumerate(page_results):
        if result['confidence'] >= 0.8:
            boundaries.append({
                'page_num': i,
                'category': result['category'],
                'confidence': result['confidence']
            })
    
    return boundaries


def get_document_type_for_page(page_index, boundaries, page_results):
    """Determine the document type for a page based on nearby boundaries."""
    if not boundaries:
        return None
    
    # Find the closest boundary before this page
    prev_boundary = None
    next_boundary = None
    
    for boundary in boundaries:
        if boundary['page_num'] <= page_index:
            prev_boundary = boundary
        elif boundary['page_num'] > page_index and next_boundary is None:
            next_boundary = boundary
            break
    
    # If we have a previous boundary and no next boundary, likely continuation
    if prev_boundary and not next_boundary:
        return prev_boundary['category']
    
    # If we have both boundaries, check distance
    if prev_boundary and next_boundary:
        prev_distance = page_index - prev_boundary['page_num']
        next_distance = next_boundary['page_num'] - page_index
        
        # If closer to previous boundary, likely continuation
        if prev_distance <= next_distance:
            return prev_boundary['category']
        else:
            return next_boundary['category']
    
    # If only next boundary exists
    if next_boundary:
        return next_boundary['category']
    
    return None


def find_context_category(page_results, current_index):
    """Find the most likely category based on context from nearby pages."""
    # Look at previous and next pages for strong indicators
    context_pages = []
    
    # Check previous pages (up to 2 pages back)
    for i in range(max(0, current_index - 2), current_index):
        if page_results[i]['confidence'] >= 0.8:
            context_pages.append(page_results[i])
    
    # Check next pages (up to 2 pages forward)
    for i in range(current_index + 1, min(len(page_results), current_index + 3)):
        if page_results[i]['confidence'] >= 0.8:
            context_pages.append(page_results[i])
    
    if not context_pages:
        return None
    
    # Find the most common high-confidence category in context
    category_counts = {}
    for page in context_pages:
        cat = page['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Return the most frequent category
    if category_counts:
        return max(category_counts, key=category_counts.get)
    
    return None


def is_likely_continuation(prev_result, current_result):
    """Check if current page is likely a continuation of the previous document."""
    prev_cat = prev_result['category']
    current_cat = current_result['category']
    
    # If categories are the same, likely continuation
    if prev_cat == current_cat:
        return True
    
    # Check for document type transitions that are unlikely
    unlikely_transitions = [
        ("Claim Form", "Reports"),
        ("Reports", "Claim Form"),
        ("KYC", "Hospital Bills"),
        ("Hospital Bills", "KYC"),
        ("Pre-Auth form C", "Reports"),
        ("Reports", "Pre-Auth form C"),
        ("Cancelled cheque", "Hospital Bills"),
        ("Hospital Bills", "Cancelled cheque"),
        ("Cancelled cheque", "Reports"),
        ("Reports", "Cancelled cheque")
    ]
    
    if (prev_cat, current_cat) in unlikely_transitions:
        return False
    
    # Check for likely document continuations
    likely_continuations = [
        ("Discharge Summary", "Discharge Summary"),
        ("Hospital Bills", "Hospital Bills"),
        ("KYC", "KYC"),
        ("Pre-Auth form C", "Pre-Auth form C"),
        ("Pharmacy Bills", "Pharmacy Bills"),
        ("Reports", "Reports")
    ]
    
    if (prev_cat, current_cat) in likely_continuations:
        return True
    
    # If previous page had high confidence, current page might be continuation
    if prev_result['confidence'] >= 0.8:
        return True
    
    return False


def analyze_document_structure(page_results):
    """Analyze the overall document structure to identify patterns."""
    if len(page_results) < 2:
        return page_results
    
    # Look for common document patterns
    patterns = {
        'hospital_sequence': ['Hospital Bills', 'Discharge Summary'],
        'kyc_sequence': ['KYC', 'KYC'],
        'preauth_sequence': ['Pre-Auth form C', 'Pre-Auth form C'],
        'claim_sequence': ['Claim Form', 'Claim Form']
    }
    
    # Apply pattern-based corrections
    corrected_results = []
    for i, result in enumerate(page_results):
        corrected_result = result.copy()
        
        # Check if this page fits a known pattern
        for pattern_name, expected_sequence in patterns.items():
            if i < len(expected_sequence):
                expected_category = expected_sequence[i]
                if (result['confidence'] < 0.7 and 
                    expected_category in [r['category'] for r in page_results[max(0, i-1):i+2]]):
                    corrected_result['category'] = expected_category
                    corrected_result['confidence'] = 0.8  # Boost confidence for pattern match
                    break
        
        corrected_results.append(corrected_result)
    
    return corrected_results


def apply_final_smoothing(page_categories, page_results):
    """
    Apply final smoothing to merge small isolated groups of pages.
    This helps merge pages that are part of the same document but were misclassified.
    """
    if len(page_categories) <= 2:
        return page_categories
    
    smoothed = page_categories.copy()
    
    # Find small isolated groups (1-2 pages) surrounded by the same category
    for i in range(1, len(smoothed) - 1):
        current_cat = smoothed[i]
        prev_cat = smoothed[i-1]
        next_cat = smoothed[i+1] if i+1 < len(smoothed) else None
        
        # If current page is isolated (different from neighbors) and neighbors are the same
        if current_cat != prev_cat and next_cat and prev_cat == next_cat:
            # Check if current page has low confidence
            if i < len(page_results) and page_results[i]['confidence'] < 0.7:
                # Check if there's no strong conflicting indicator
                page_text = page_results[i].get('page_text', '')
                if not has_conflicting_indicators(page_text, prev_cat):
                    smoothed[i] = prev_cat
        
        # If we have a small group (1-2 pages) of one category between larger groups of another
        # Check if we should merge it
        if i > 0 and i < len(smoothed) - 1:
            # Look for patterns like: A, B, B, A or A, B, A
            if smoothed[i-1] == smoothed[i+1] and smoothed[i] != smoothed[i-1]:
                # Check if the isolated group is small and has low confidence
                group_size = 1
                if i > 1 and smoothed[i-2] == smoothed[i]:
                    group_size = 2
                if i < len(smoothed) - 2 and smoothed[i+2] == smoothed[i]:
                    group_size = max(group_size, 2)
                
                # If it's a small isolated group (1-2 pages) with low confidence, merge it
                if group_size <= 2:
                    avg_confidence = 0.0
                    count = 0
                    for j in range(max(0, i-group_size), min(len(page_results), i+group_size+1)):
                        if smoothed[j] == smoothed[i]:
                            avg_confidence += page_results[j]['confidence']
                            count += 1
                    if count > 0:
                        avg_confidence /= count
                        
                        # If average confidence is low, merge with surrounding category
                        if avg_confidence < 0.65:
                            page_text = page_results[i].get('page_text', '')
                            if not has_conflicting_indicators(page_text, smoothed[i-1]):
                                smoothed[i] = smoothed[i-1]
                                if group_size == 2 and i > 0:
                                    smoothed[i-1] = smoothed[i-1]
    
    return smoothed


def apply_aggressive_merging(page_categories, page_results):
    """
    Apply aggressive merging to group consecutive pages more effectively.
    This uses a sliding window approach to identify dominant categories and merge isolated pages.
    """
    if len(page_categories) <= 2:
        return page_categories
    
    merged = page_categories.copy()
    window_size = 3  # Look at 3 pages before and after
    
    # First, identify high-confidence anchor pages
    anchor_pages = []
    for i, result in enumerate(page_results):
        if result['confidence'] >= 0.8:
            anchor_pages.append((i, result['category']))
    
    # Use anchor pages to determine regions
    if len(anchor_pages) < 2:
        # Not enough anchors, use simpler approach
        return apply_simple_merging(merged, page_results)
    
    # Create regions based on anchor pages
    regions = []
    for i in range(len(anchor_pages)):
        start_idx = anchor_pages[i][0]
        end_idx = anchor_pages[i+1][0] if i+1 < len(anchor_pages) else len(merged)
        category = anchor_pages[i][1]
        regions.append((start_idx, end_idx, category))
    
    # Merge pages in each region to the dominant category
    for start_idx, end_idx, dominant_cat in regions:
        # Count categories in this region
        category_counts = {}
        for i in range(start_idx, end_idx):
            cat = merged[i]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Find the most common category in this region
        if category_counts:
            most_common_cat = max(category_counts, key=category_counts.get)
            
            # If the most common category matches the anchor, use it for all pages in region
            if most_common_cat == dominant_cat:
                for i in range(start_idx, end_idx):
                    # Only change if confidence is low or if it's a small isolated group
                    if page_results[i]['confidence'] < 0.75:
                        # Check for conflicting indicators
                        page_text = page_results[i].get('page_text', '')
                        if not has_conflicting_indicators(page_text, dominant_cat):
                            merged[i] = dominant_cat
    
    # Apply simple merging for any remaining isolated groups
    merged = apply_simple_merging(merged, page_results)
    
    return merged


def apply_simple_merging(page_categories, page_results):
    """
    Simple merging: merge small isolated groups (1-2 pages) into surrounding dominant category.
    """
    if len(page_categories) <= 2:
        return page_categories
    
    merged = page_categories.copy()
    
    # Pass 1: Merge single isolated pages
    for i in range(1, len(merged) - 1):
        if merged[i] != merged[i-1] and merged[i] != merged[i+1]:
            # Isolated page - check if we should merge it
            if page_results[i]['confidence'] < 0.7:
                # Check which neighbor has higher confidence
                prev_conf = page_results[i-1]['confidence']
                next_conf = page_results[i+1]['confidence']
                
                if prev_conf > next_conf and prev_conf >= 0.6:
                    page_text = page_results[i].get('page_text', '')
                    if not has_conflicting_indicators(page_text, merged[i-1]):
                        merged[i] = merged[i-1]
                elif next_conf > prev_conf and next_conf >= 0.6:
                    page_text = page_results[i].get('page_text', '')
                    if not has_conflicting_indicators(page_text, merged[i+1]):
                        merged[i] = merged[i+1]
                elif merged[i-1] == merged[i+1]:
                    # Both neighbors are the same, merge to that
                    page_text = page_results[i].get('page_text', '')
                    if not has_conflicting_indicators(page_text, merged[i-1]):
                        merged[i] = merged[i-1]
    
    # Pass 2: Merge small groups (2 pages) that are isolated
    for i in range(1, len(merged) - 2):
        # Check for pattern: A, B, B, A (where B is a 2-page group)
        if (merged[i-1] == merged[i+2] and 
            merged[i] == merged[i+1] and 
            merged[i] != merged[i-1]):
            # Small group of 2 pages - check if we should merge
            avg_conf = (page_results[i]['confidence'] + page_results[i+1]['confidence']) / 2
            neighbor_conf = max(page_results[i-1]['confidence'], page_results[i+2]['confidence'])
            
            if avg_conf < 0.7 and neighbor_conf >= 0.6:
                # Check for conflicting indicators
                page_text_i = page_results[i].get('page_text', '')
                page_text_i1 = page_results[i+1].get('page_text', '')
                if (not has_conflicting_indicators(page_text_i, merged[i-1]) and
                    not has_conflicting_indicators(page_text_i1, merged[i-1])):
                    merged[i] = merged[i-1]
                    merged[i+1] = merged[i-1]
    
    # Pass 3: Use sliding window to determine dominant category
    window = 5
    for i in range(len(merged)):
        if page_results[i]['confidence'] < 0.7:
            # Look at surrounding pages in window
            start = max(0, i - window)
            end = min(len(merged), i + window + 1)
            
            category_counts = {}
            confidence_sum = {}
            for j in range(start, end):
                if j != i:
                    cat = merged[j]
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                    confidence_sum[cat] = confidence_sum.get(cat, 0) + page_results[j]['confidence']
            
            if category_counts:
                # Find category with highest weighted score (count * avg_confidence)
                best_cat = None
                best_score = 0
                for cat, count in category_counts.items():
                    avg_conf = confidence_sum[cat] / count
                    score = count * avg_conf
                    if score > best_score:
                        best_score = score
                        best_cat = cat
                
                if best_cat and best_cat != merged[i]:
                    # Check for conflicting indicators
                    page_text = page_results[i].get('page_text', '')
                    if not has_conflicting_indicators(page_text, best_cat):
                        merged[i] = best_cat
    
    return merged


def apply_pattern_based_correction(page_categories, page_results):
    """
    Apply pattern-based corrections for common misclassification scenarios.
    This looks for specific patterns and corrects them based on document structure.
    """
    if len(page_categories) < 3:
        return page_categories
    
    corrected = page_categories.copy()
    
    # Pattern 1: Claim Form at start, then other category, then Claim Form again
    # This suggests the middle pages might be Claim Form continuation
    if (corrected[0] == "Claim Form" and 
        len(corrected) > 5 and
        any(corrected[i] == "Claim Form" for i in range(5, min(10, len(corrected))))):
        
        # Find the first Claim Form after the initial group
        first_claim_after = None
        for i in range(1, min(10, len(corrected))):
            if corrected[i] == "Claim Form" and i > 3:
                first_claim_after = i
                break
        
        if first_claim_after:
            # Check if pages between initial Claim Form and this one should be Claim Form
            # Look at the category distribution
            initial_claim_end = 0
            for i in range(len(corrected)):
                if corrected[i] != "Claim Form":
                    initial_claim_end = i
                    break
            
            # If there's a gap, check if it should be filled with Claim Form
            if initial_claim_end < first_claim_after:
                # Check confidence of pages in the gap
                gap_pages = corrected[initial_claim_end:first_claim_after]
                avg_confidence = sum(page_results[i]['confidence'] 
                                    for i in range(initial_claim_end, first_claim_after)) / len(gap_pages)
                
                # If average confidence is low, likely continuation of Claim Form
                if avg_confidence < 0.75:
                    # Check if any page has strong conflicting indicators
                    should_merge = True
                    for i in range(initial_claim_end, first_claim_after):
                        page_text = page_results[i].get('page_text', '')
                        if has_conflicting_indicators(page_text, "Claim Form"):
                            should_merge = False
                            break
                    
                    if should_merge:
                        for i in range(initial_claim_end, first_claim_after):
                            corrected[i] = "Claim Form"
    
    # Pattern 1b: Claim Form sequence at start - extend if next pages don't have strong headers
    # BUT stop immediately if we encounter Discharge Summary indicators
    if len(corrected) >= 5 and corrected[0] == "Claim Form":
        # Find where Claim Form sequence ends
        claim_end = 0
        for i in range(len(corrected)):
            if corrected[i] != "Claim Form":
                claim_end = i
                break
        else:
            claim_end = len(corrected)
        
        # If we have at least 3 Claim Form pages and next page might be continuation
        if claim_end >= 3 and claim_end < len(corrected):
            next_page_idx = claim_end
            next_page_text = page_results[next_page_idx].get('page_text', '')
            next_header = has_document_header(next_page_text)
            
            # CRITICAL: Check for Discharge Summary indicators first
            processed_text = preprocess_text_for_header_detection(next_page_text)
            text_lower = processed_text.lower()
            header = text_lower[:800]
            
            # STRONG Discharge Summary indicators that should stop Claim Form extension
            # Only use the strongest indicators to avoid false positives
            strong_discharge_indicators = [
                r'\bdischarge\s*summary\b',  # Must have this
                r'\bdischarge\s*note\b'
            ]
            
            # Weaker indicators that might appear in Claim Forms too
            weak_discharge_indicators = [
                r'\bcondition\s*(on|at)\s*discharge\b',
                r'\btreatment\s*given\s*in\s*hospital\b',
                r'\bpatient\s*name.*age.*sex\b',
                r'\bdiagnosis\b.*\btreatment\b',
                r'\bfollow\s*up\s*(note|advice)\b'
            ]
            
            has_strong_discharge = any(re.search(pattern, header, re.IGNORECASE) 
                                      for pattern in strong_discharge_indicators)
            has_weak_discharge = any(re.search(pattern, header, re.IGNORECASE) 
                                    for pattern in weak_discharge_indicators)
            
            # Check for Claim Form indicators on this page
            claim_indicators = [
                r'\bclaim\s*form\b',
                r'\bclaim\s*no[.:]?\b',
                r'\bpolicy\s*(no|number)\b',
                r'\btotal\s*amount\s*claimed\b',
                r'\breimbursement\b'
            ]
            has_claim_indicators = any(re.search(pattern, header, re.IGNORECASE) 
                                     for pattern in claim_indicators)
            
            # Decision logic:
            # - If page has STRONG Discharge Summary header, don't extend Claim Form
            # - If page 5 (index 4) and has weak discharge indicators BUT also has claim indicators, extend Claim Form
            # - If page 6+ (index 5+), don't extend Claim Form if it has discharge indicators
            if next_header == "Discharge Summary" or has_strong_discharge:
                # Don't extend - this is clearly Discharge Summary
                pass
            elif next_page_idx == 4:  # Page 5 (0-indexed)
                # For page 5, be more lenient - extend Claim Form if:
                # - It doesn't have strong Discharge Summary header, AND
                # - It has Claim Form indicators OR is likely continuation
                if has_claim_indicators or is_likely_continuation_page(next_page_text, "Claim Form"):
                    corrected[next_page_idx] = "Claim Form"
                elif has_weak_discharge and not has_claim_indicators:
                    # Has weak discharge indicators but no claim indicators - might be Discharge Summary
                    # But only if confidence is low
                    if page_results[next_page_idx]['confidence'] < 0.7:
                        pass  # Don't extend, let it be Discharge Summary
                    else:
                        # Medium confidence - extend Claim Form
                        corrected[next_page_idx] = "Claim Form"
                else:
                    # No clear indicators - extend Claim Form if it's a continuation
                    if is_likely_continuation_page(next_page_text, "Claim Form"):
                        corrected[next_page_idx] = "Claim Form"
            elif next_page_idx < 4:  # Pages 1-4
                # For earlier pages, always extend if it's a continuation
                if is_likely_continuation_page(next_page_text, "Claim Form"):
                    corrected[next_page_idx] = "Claim Form"
    
    # Pattern 2: Hospital Bills with isolated Claim Form pages in between
    # This suggests those isolated pages might be Hospital Bills continuation
    hospital_bill_regions = []
    start = None
    for i, cat in enumerate(corrected):
        if cat == "Hospital Bills":
            if start is None:
                start = i
        else:
            if start is not None:
                hospital_bill_regions.append((start, i))
                start = None
    if start is not None:
        hospital_bill_regions.append((start, len(corrected)))
    
    # For each Hospital Bills region, check for isolated Claim Form pages
    for start_idx, end_idx in hospital_bill_regions:
        if end_idx - start_idx > 2:  # Only for regions with more than 2 pages
            for i in range(start_idx, end_idx):
                if corrected[i] == "Claim Form":
                    # Check if this is an isolated Claim Form in a Hospital Bills region
                    prev_cat = corrected[i-1] if i > 0 else None
                    next_cat = corrected[i+1] if i+1 < len(corrected) else None
                    
                    if (prev_cat == "Hospital Bills" or next_cat == "Hospital Bills"):
                        # Check confidence
                        if page_results[i]['confidence'] < 0.75:
                            page_text = page_results[i].get('page_text', '')
                            if not has_conflicting_indicators(page_text, "Hospital Bills"):
                                corrected[i] = "Hospital Bills"
    
    # Pattern 3: Discharge Summary detection and protection
    # If pages have Discharge Summary indicators but were classified as something else, correct them
    for i in range(len(corrected)):
        page_text = page_results[i].get('page_text', '')
        processed_text = preprocess_text_for_header_detection(page_text)
        text_lower = processed_text.lower()
        header = text_lower[:800]
        full_text = text_lower  # Check full text too
        
        # Check for Discharge Summary indicators (both in header and body)
        discharge_indicators = [
            r'\bdischarge\s*summary\b',
            r'\bdischarge\s*note\b',
            r'\bcondition\s*(on|at)\s*discharge\b',
            r'\btreatment\s*given\s*in\s*hospital\b',
            r'\bdiagnosis\b.*\btreatment\b',
            r'\bfollow\s*up\s*(note|advice)\b',
            r'\bpatient\s*name.*age.*sex.*admission\b'  # Common discharge summary pattern
        ]
        
        has_discharge_header = any(re.search(pattern, header, re.IGNORECASE) 
                                  for pattern in discharge_indicators)
        has_discharge_body = any(re.search(pattern, full_text, re.IGNORECASE) 
                                for pattern in discharge_indicators[:4])  # Check key patterns in full text
        
        # Check for billing indicators to distinguish from Hospital Bills
        has_billing_info = any(term in text_lower for term in [
            "bill no", "bill number", "total amount", "charges", "gst", "invoice",
            "item code", "rate", "amount", "sgst", "cgst", "tax", "final bill"
        ])
        
        # Check for clinical indicators (stronger for Discharge Summary)
        has_clinical_info = any(term in text_lower for term in [
            "diagnosis", "treatment given", "admission date", "discharge date",
            "clinical summary", "follow up", "medication", "procedure", "condition on discharge"
        ])
        
        # If page has Discharge Summary header, it should be Discharge Summary
        page_header = has_document_header(page_text)
        if page_header == "Discharge Summary":
            corrected[i] = "Discharge Summary"
        # If page has strong Discharge Summary indicators and was misclassified, correct it
        # Check for Claim Form, Hospital Bills, or Pharmacy Bills that should be Discharge Summary
        elif (has_discharge_header or has_discharge_body) and corrected[i] in ["Claim Form", "Hospital Bills", "Pharmacy Bills"]:
            # Check for STRONG Discharge Summary header (not just body indicators)
            strong_discharge_patterns = [
                r'\bdischarge\s*summary\b',  # Must have this in header
                r'\bdischarge\s*note\b'
            ]
            has_strong_discharge_header = any(re.search(pattern, header, re.IGNORECASE) 
                                             for pattern in strong_discharge_patterns)
            
            # For pages 5-9 (indices 4-8), prioritize Discharge Summary if it has clinical info
            # and doesn't have strong billing indicators
            if 4 <= i <= 8:  # Pages 5-9 (0-indexed)
                # Check if it has clinical info but not strong billing info
                if has_clinical_info and (has_strong_discharge_header or not has_billing_info):
                    # Check for conflicting indicators
                    claim_indicators = [
                        r'\bclaim\s*form\b',
                        r'\bclaim\s*no[.:]?\b',
                        r'\bpolicy\s*(no|number)\b',
                        r'\btotal\s*amount\s*claimed\b'
                    ]
                    has_strong_claim = any(re.search(pattern, header, re.IGNORECASE) 
                                         for pattern in claim_indicators)
                    
                    # If it's Hospital Bills or Pharmacy Bills with discharge indicators, convert
                    if corrected[i] in ["Hospital Bills", "Pharmacy Bills"]:
                        if has_strong_discharge_header or (has_clinical_info and not has_billing_info):
                            if not has_strong_claim:
                                corrected[i] = "Discharge Summary"
                    # If it's Claim Form, be more conservative
                    elif corrected[i] == "Claim Form":
                        if has_strong_discharge_header and not has_strong_claim:
                            if page_results[i]['confidence'] < 0.85:
                                corrected[i] = "Discharge Summary"
            # For pages 6+ (i >= 5), check if it should be Discharge Summary
            elif i >= 5:  # Pages 6+ (0-indexed, so i=5 is page 6)
                # Check confidence - if low or medium, likely misclassified
                if page_results[i]['confidence'] < 0.85:
                    # Also check if it doesn't have strong Claim Form indicators
                    claim_indicators = [
                        r'\bclaim\s*form\b',
                        r'\bclaim\s*no[.:]?\b',
                        r'\bpolicy\s*(no|number)\b',
                        r'\btotal\s*amount\s*claimed\b'
                    ]
                    has_strong_claim = any(re.search(pattern, header, re.IGNORECASE) 
                                         for pattern in claim_indicators)
                    
                    # If it's Hospital Bills or Pharmacy Bills with discharge indicators, convert
                    if corrected[i] in ["Hospital Bills", "Pharmacy Bills"]:
                        if has_strong_discharge_header or (has_clinical_info and not has_billing_info):
                            if not has_strong_claim:
                                corrected[i] = "Discharge Summary"
                    # If it's Claim Form
                    elif corrected[i] == "Claim Form":
                        if not has_strong_claim:
                            corrected[i] = "Discharge Summary"
            elif i == 4 and has_strong_discharge_header:  # Page 5 (index 4) with STRONG header
                # Only convert page 5 if it has a very clear Discharge Summary header
                # AND doesn't have Claim Form indicators
                claim_indicators = [
                    r'\bclaim\s*form\b',
                    r'\bclaim\s*no[.:]?\b',
                    r'\bpolicy\s*(no|number)\b'
                ]
                has_strong_claim = any(re.search(pattern, header, re.IGNORECASE) 
                                     for pattern in claim_indicators)
                
                if not has_strong_claim and page_results[i]['confidence'] < 0.8:
                    corrected[i] = "Discharge Summary"
    
    # Pattern 4: Discharge Summary in middle of other document types
    # If Discharge Summary is surrounded by same category on both sides, might be misclassified
    for i in range(1, len(corrected) - 1):
        if corrected[i] == "Discharge Summary":
            prev_cat = corrected[i-1]
            next_cat = corrected[i+1] if i+1 < len(corrected) else None
            
            # If surrounded by same category (and it's not Discharge Summary), check if should merge
            # BUT only if Discharge Summary indicators are weak
            if next_cat and prev_cat == next_cat and prev_cat != "Discharge Summary":
                page_text = page_results[i].get('page_text', '')
                page_header = has_document_header(page_text)
                
                # If page has strong Discharge Summary header, don't merge
                if page_header == "Discharge Summary":
                    continue  # Keep as Discharge Summary
                
                # Check if this is a small group
                group_size = 1
                if i > 1 and corrected[i-2] == "Discharge Summary":
                    group_size += 1
                if i+2 < len(corrected) and corrected[i+2] == "Discharge Summary":
                    group_size += 1
                
                # If small group with low confidence, might be continuation
                if group_size <= 2:
                    avg_conf = sum(page_results[j]['confidence'] 
                                  for j in range(max(0, i-group_size+1), min(len(corrected), i+group_size))) / group_size
                    if avg_conf < 0.75:
                        # Check for Discharge Summary indicators
                        processed_text = preprocess_text_for_header_detection(page_text)
                        text_lower = processed_text.lower()
                        header = text_lower[:800]
                        
                        discharge_indicators = [
                            r'\bdischarge\s*summary\b',
                            r'\bdischarge\s*note\b',
                            r'\bcondition\s*(on|at)\s*discharge\b'
                        ]
                        
                        has_discharge = any(re.search(pattern, header, re.IGNORECASE) 
                                          for pattern in discharge_indicators)
                        
                        # Only merge if no strong Discharge Summary indicators
                        if not has_discharge and not has_conflicting_indicators(page_text, prev_cat):
                            corrected[i] = prev_cat
                            if group_size == 2 and i > 0:
                                corrected[i-1] = prev_cat
    
    # Pattern 5: Distinguish Hospital Bills from Pharmacy Bills
    # Hospital Bills typically have: room charges, procedure charges, consultation fees, itemized hospital services
    # Pharmacy Bills typically have: medication names, drug names, tablets, capsules, syrups
    # For pages 10+ (indices 9+), if classified as Pharmacy Bills but has hospital billing indicators, convert to Hospital Bills
    for i in range(len(corrected)):
        if corrected[i] == "Pharmacy Bills" and i >= 9:  # Pages 10+ (0-indexed, so i=9 is page 10)
            page_text = page_results[i].get('page_text', '')
            processed_text = preprocess_text_for_header_detection(page_text)
            text_lower = processed_text.lower()
            
            # Check for Hospital Bills indicators
            hospital_bill_indicators = [
                r'\bfinal\s*bill\b',
                r'\bhospital.*bill\b',
                r'\bbill\s*no[.:]?\b',
                r'\bbill\s*number\b',
                r'\broom\s*charges?\b',
                r'\bprocedure\s*charges?\b',
                r'\bconsultation\s*fees?\b',
                r'\bitem\s*code\b',
                r'\bgstn\b',
                r'\bsgst\b',
                r'\bcgst\b',
                r'\btotal\s*bill\s*amt\b',
                r'\bnet\s*bill\s*amt\b',
                r'\bip\s*no\b',
                r'\bward\s*name\b',
                r'\bbed\s*no\b',
                r'\blos\b'  # Length of stay
            ]
            
            # Check for Pharmacy Bills indicators
            pharmacy_bill_indicators = [
                r'\bpharmacy\b',
                r'\bmedical\s*store\b',
                r'\bchemist\b',
                r'\bdrugstore\b',
                r'\bdispensary\b',
                r'\btablet\b',
                r'\bcapsule\b',
                r'\bsyrup\b',
                r'\binjection\b',
                r'\bprescription\b',
                r'\bdosage\b',
                r'\bmrp\b',
                r'\bretail\s*price\b'
            ]
            
            has_hospital_bill_indicators = any(re.search(pattern, text_lower, re.IGNORECASE) 
                                              for pattern in hospital_bill_indicators)
            has_pharmacy_bill_indicators = any(re.search(pattern, text_lower, re.IGNORECASE) 
                                               for pattern in pharmacy_bill_indicators)
            
            # If it has hospital billing indicators but not strong pharmacy indicators, convert to Hospital Bills
            if has_hospital_bill_indicators and not has_pharmacy_bill_indicators:
                # Also check if it doesn't have Discharge Summary indicators
                discharge_indicators = [
                    r'\bdischarge\s*summary\b',
                    r'\bdischarge\s*note\b',
                    r'\bcondition\s*(on|at)\s*discharge\b',
                    r'\btreatment\s*given\s*in\s*hospital\b'
                ]
                has_discharge = any(re.search(pattern, text_lower, re.IGNORECASE) 
                                   for pattern in discharge_indicators)
                
                if not has_discharge:
                    corrected[i] = "Hospital Bills"
            # If it has both but hospital indicators are stronger (e.g., "FINAL BILL"), prefer Hospital Bills
            elif has_hospital_bill_indicators and has_pharmacy_bill_indicators:
                # Check for strong hospital bill header
                header = text_lower[:500]
                if re.search(r'\bfinal\s*bill\b', header, re.IGNORECASE) or re.search(r'\bhospital.*bill\b', header, re.IGNORECASE):
                    corrected[i] = "Hospital Bills"
    
    return corrected


def apply_structure_based_correction(page_categories, page_results):
    """
    Apply structure-based correction using majority voting in sliding windows.
    This helps correct pages that are misclassified but are part of a larger document group.
    """
    if len(page_categories) < 3:
        return page_categories
    
    corrected = page_categories.copy()
    window_size = 5  # Use a 5-page sliding window
    
    # For each page, look at surrounding pages to determine most likely category
    for i in range(len(corrected)):
        # Skip if confidence is very high (0.9+)
        if page_results[i]['confidence'] >= 0.9:
            continue
        
        # Calculate window boundaries
        start = max(0, i - window_size // 2)
        end = min(len(corrected), i + window_size // 2 + 1)
        
        # Count categories in window, weighted by confidence
        category_scores = {}
        for j in range(start, end):
            if j != i:  # Don't count the current page
                cat = corrected[j]
                conf = page_results[j]['confidence']
                category_scores[cat] = category_scores.get(cat, 0) + conf
        
        if category_scores:
            # Find category with highest weighted score
            best_cat = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_cat]
            
            # Calculate average confidence for best category
            count = sum(1 for j in range(start, end) 
                       if j != i and corrected[j] == best_cat)
            avg_conf = best_score / count if count > 0 else 0
            
            # If best category is different and has good support, consider changing
            if (best_cat != corrected[i] and 
                avg_conf >= 0.65 and 
                count >= 2):  # At least 2 pages support this category
                
                # Check for conflicting indicators
                page_text = page_results[i].get('page_text', '')
                if not has_conflicting_indicators(page_text, best_cat):
                    # Only change if current confidence is not too high
                    if page_results[i]['confidence'] < 0.8:
                        corrected[i] = best_cat
    
    # Additional pass: Merge small isolated groups more aggressively
    # Look for patterns where a single page or small group is different from neighbors
    for i in range(1, len(corrected) - 1):
        if (corrected[i] != corrected[i-1] and 
            corrected[i] != corrected[i+1] and
            corrected[i-1] == corrected[i+1]):
            # Single isolated page - merge to neighbor category if confidence is low
            if page_results[i]['confidence'] < 0.75:
                page_text = page_results[i].get('page_text', '')
                if not has_conflicting_indicators(page_text, corrected[i-1]):
                    corrected[i] = corrected[i-1]
    
    return corrected


def ensure_preauth_continuation(page_categories, page_results):
    """
    Ensure that if pages 1-3 are Pre-Auth form C, page 4 is also Pre-Auth form C
    unless it has a STRONG Discharge Summary header.
    This handles the case where page 4 is a continuation of the Pre-Auth form C document.
    """
    if len(page_categories) < 4:
        return page_categories
    
    corrected = page_categories.copy()
    
    # Check if pages 1-3 (indices 0-2) are all Pre-Auth form C
    if all(corrected[i] == "Pre-Auth form C" for i in range(3)):
        # Page 4 (index 3) should be Pre-Auth form C unless it has a STRONG Discharge Summary header
        page_4_idx = 3
        page_4_text = page_results[page_4_idx].get('page_text', '')
        
        # Check for STRONG Discharge Summary header
        page_4_header = has_document_header(page_4_text)
        
        if page_4_header == "Discharge Summary":
            # Has clear Discharge Summary header - keep as Discharge Summary
            pass
        else:
            # Check for strong Discharge Summary indicators in header
            processed_text = preprocess_text_for_header_detection(page_4_text)
            text_lower = processed_text.lower()
            header = text_lower[:800]
            
            # Strong Discharge Summary indicator
            strong_discharge = re.search(r'\bdischarge\s*summary\b', header, re.IGNORECASE)
            
            # Check for Pre-Auth form C indicators
            preauth_indicators = [
                r'\bpre[\s\-]*auth\b',
                r'\bpre[\s\-]*approval\b',
                r'\brequest\s*for\s*cashless\s*hospitali[sz]ation\b',
                r'\bproposed\s*(treatment|date|hospitalization)\b',
                r'\bestimated\s*(expenses|cost)\b',
                r'\bauthorized\s*limit\b',
                r'\bto\s*be\s*filled\s*by\s*insured\b'
            ]
            has_preauth = any(re.search(pattern, header, re.IGNORECASE) 
                            for pattern in preauth_indicators)
            
            # If no strong Discharge Summary header, make it Pre-Auth form C
            if not strong_discharge:
                # Check if it's a continuation
                if is_likely_continuation_page(page_4_text, "Pre-Auth form C") or has_preauth:
                    corrected[page_4_idx] = "Pre-Auth form C"
                elif page_results[page_4_idx]['confidence'] < 0.75:
                    # Low confidence - likely continuation
                    corrected[page_4_idx] = "Pre-Auth form C"
    
    return corrected


def ensure_claim_form_continuation(page_categories, page_results):
    """
    Ensure that if pages 1-4 are Claim Form, page 5 is also Claim Form
    unless it has a STRONG Discharge Summary header.
    """
    if len(page_categories) < 5:
        return page_categories
    
    corrected = page_categories.copy()
    
    # Check if pages 1-4 (indices 0-3) are all Claim Form
    if all(corrected[i] == "Claim Form" for i in range(4)):
        # Page 5 (index 4) should be Claim Form unless it has a STRONG Discharge Summary header
        page_5_idx = 4
        page_5_text = page_results[page_5_idx].get('page_text', '')
        
        # Check for STRONG Discharge Summary header
        page_5_header = has_document_header(page_5_text)
        
        if page_5_header == "Discharge Summary":
            # Has clear Discharge Summary header - keep as Discharge Summary
            pass
        else:
            # Check for strong Discharge Summary indicators in header
            processed_text = preprocess_text_for_header_detection(page_5_text)
            text_lower = processed_text.lower()
            header = text_lower[:800]
            
            # Only the strongest indicator
            strong_discharge = re.search(r'\bdischarge\s*summary\b', header, re.IGNORECASE)
            
            # Check for Claim Form indicators
            claim_indicators = [
                r'\bclaim\s*form\b',
                r'\bclaim\s*no[.:]?\b',
                r'\bpolicy\s*(no|number)\b',
                r'\breimbursement\b'
            ]
            has_claim = any(re.search(pattern, header, re.IGNORECASE) 
                          for pattern in claim_indicators)
            
            # If no strong Discharge Summary header, make it Claim Form
            if not strong_discharge:
                # Check if it's a continuation
                if is_likely_continuation_page(page_5_text, "Claim Form") or has_claim:
                    corrected[page_5_idx] = "Claim Form"
                elif page_results[page_5_idx]['confidence'] < 0.75:
                    # Low confidence - likely continuation
                    corrected[page_5_idx] = "Claim Form"
    
    return corrected


def process_file(uploaded_file):
    """Process uploaded file based on its type."""
    file_extension = uploaded_file.name.lower().split('.')[-1]

    if file_extension == 'pdf':
        # Process PDF directly - now returns list of page texts
        uploaded_file.seek(0)
        page_texts = extract_text_from_pdf(uploaded_file)
        return page_texts, "PDF"

    elif file_extension in ['tiff', 'tif']:
        # Convert TIFF to PDF and then process
        uploaded_file.seek(0)
        tiff_bytes = uploaded_file.read()

        # First, try direct OCR on TIFF for better quality
        extracted_text = extract_text_from_tiff(tiff_bytes)
        return [extracted_text], "TIFF"  # Return as list for consistency

    else:
        return [f"Unsupported file format: {file_extension}"], "Unknown"


def main():
    st.set_page_config(
        page_title="Document Categorization App",
        page_icon="📄",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    st.title("📄 Multi-Page Document Categorization")
    st.subheader("Automatically categorize each page of your PDF and TIFF documents")

    # Check which APIs are available and select automatically
    openai_available = openai_client is not None
    gemini_available = gemini_client is not None
    
    if not openai_available and not gemini_available:
        st.error("❌ No API keys found! Please set either OPENAI_API_KEY or GEMINI_API_KEY in your environment variables.")
        st.stop()
    
    # Automatically select API provider (prefer OpenAI, fallback to Gemini)
    if openai_available:
        api_provider = "openai"
    elif gemini_available:
        api_provider = "gemini"
    else:
        api_provider = "openai"  # Default fallback

    # Display file type and extension mapping
    st.markdown("**File Type and Extension Mapping:**")
    file_type_table = "| File Type | Extension |\n|---|---|\n"
    for file_type, ext in FILE_TYPE_EXTENSIONS.items():
        file_type_table += f"| {file_type} | {ext} |\n"
    # st.markdown(file_type_table)

    uploaded_file = st.file_uploader(
        "Upload your document",
        type=["pdf", "tiff", "tif"],
        help="Supported formats: PDF, TIFF, TIF"
    )

    if uploaded_file is not None:
        # Display file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
            "File type": uploaded_file.name.lower().split('.')[-1].upper()
        }
        st.write("**File Details:**")
        for key, value in file_details.items():
            st.write(f"- {key}: {value}")

        with st.spinner("Processing document..."):
            # Process the file based on its type
            page_texts, file_type = process_file(uploaded_file)

            if page_texts[0].startswith("Error") or page_texts[0].startswith("Unsupported"):
                st.error(page_texts[0])
            elif "No text could be extracted" in page_texts[0]:
                st.error(page_texts[0])
            else:
                # Text extraction successful, now categorize each page
                with st.spinner(f"Categorizing {len(page_texts)} page(s) using {api_provider.upper()}..."):
                    grouped_results, page_categories = categorize_multi_page_document(page_texts, api_provider)

                # Display results with nice formatting
                st.success(f"Document processed successfully! ({len(page_texts)} page(s) processed as {file_type})")

                st.subheader("📋 Document Classification Results")
                
                # Display compact format (expected output format) - PRIMARY OUTPUT
                compact_output = format_output_compact(page_categories)
                st.markdown("### **Document Categorization:**")
                st.info(f"**{compact_output}**")
                st.markdown("---")
                
                # Display detailed grouped results (for debugging/reference)
                with st.expander("📄 Page-by-Page Classification (Detailed)", expanded=False):
                    for result in grouped_results:
                        st.write(f"📄 {result}")
                
                # Add debug information if requested
                with st.expander("🔍 Debug Information (Confidence Scores)"):
                    st.write("**Individual Page Analysis:**")
                    for i, page_text in enumerate(page_texts):
                        if not (page_text.startswith("Error") or "No text could be extracted" in page_text):
                            result = categorize_document_with_confidence(page_text, api_provider)
                            st.write(f"Page {i+1}: {result['category']} (Confidence: {result['confidence']:.2f})")
                        else:
                            st.write(f"Page {i+1}: Others (Confidence: 0.00) - Error in text extraction")

                # Create a summary of document types found
                unique_categories = list(set(page_categories))
                st.subheader("📊 Summary")
                st.write(f"**Total Pages:** {len(page_texts)}")
                st.write(f"**Document Types Found:** {len(unique_categories)}")
                
                # Display categories with counts
                category_counts = {}
                for category in page_categories:
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                st.write("**Category Distribution:**")
                for category, count in category_counts.items():
                    st.write(f"- {category}: {count} page(s)")

                # Add option to see extracted text for each page
                with st.expander("View extracted text by page"):
                    for i, page_text in enumerate(page_texts):
                        st.write(f"**Page {i+1} ({page_categories[i]}):**")
                        st.text_area(
                            f"Text from page {i+1}",
                            page_text,
                            height=200,
                            key=f"page_{i+1}"
                        )


if __name__ == "__main__":
    main()
