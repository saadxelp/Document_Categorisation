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
        "Claim Form", "Insurance Claim", "Medical Claim", "Health Claim", "Reimbursement Claim",
        "Policy Holder", "Policy Number", "Sum Insured", "Insured Person", "Insurance Details",
        "Claim Number", "Claim Reference", "Claim Amount", "Claim Date", "Claim Submission",
        "Insurer", "Insurance Company", "Health Insurance", "Medical Insurance", "Policy Details",
        "Claimant", "Claimant Name", "Claimant Address", "Claimant Contact", "Claimant Signature",
        "Declaration", "I hereby declare", "Signature of the Insured", "Date of Declaration"
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
        "cardiological investigation", "balance due", "net bill amt", "total bill amt"
    ],
    "Pharmacy Bills": [
        "Name_Of_Biller", "Address_Of_Biller", "Address_Lines", "City", "State", "Pincode", "Name_Of_Patient", "Bill_Date", "Bill_No.", "Treating_Dr", "Bill_Items", "Sr_No", "Batch_No", "Expiry_No", "Description", "Unit", "Unit_Price", "Discount", "Actual_Price", "Is_Nme", "Is_Returned", "Expense_Category", "Expense_Code", "Name_Of_Implant", "Implant_Sticker_Number", "Total_Discount", "Total_Amount",
        "Pharmacy", "Drug", "Medicine", "Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Prescription", "Dosage", "MRP", "Retail Price", "Medication", "Chemist", "Pharmacy Bill", "Medical Store", "Drugstore", "Dispensary", "Rx", "Prescribed", "Refill"
    ],
    "Diagnostic Bills": [
        "Name_Of_Biller", "Address_Of_Biller", "Address_Lines", "City", "State", "Pincode", "Bill_Date", "Bill_No", "Bill_Line_Items", "Name_Of_Test", "Price", "Is_Nme", "Total_Discount", "Total_Amount_Paid"
    ],
    "KYC": [
        "Proof_Type", "Name", "Date_Of_Birth", "Is_Id_Proof", "Is_Address_Proof"
    ],
    "Pre-Auth form C": [
        "Family_Physician", "Exists", "Name", "Insured_Card_Id_Number", "Policy_Number_Or_Name_Of_Corporate", "Employee_Id", "Contact_No", "Present_Illness", "Duration_Of_Present_Ailment", "Date_Of_First_Consultation", "Provisional_Diagnosis", "Proposed_Line_Of_Treatment", "Name_Of_Surgery_If_Yes", "Date_Of_Admission", "Room_Type", "Per_Day_Room_Nursing_Diet_Charges", "Expected_Cost_Diagnostics_Investigation", "Icu_Charges", "Ot_Charges", "Surgeon_Anaesthetist_Consultation_Charges", "Medicine_Consumables_Implant_Charges", "Other_Hospital_Expenses", "All_Inclusive_Package_Charges", "Total_Expected_Cost", "Past_History_Of_Chronic_Illnesses", "Diabetes", "Hypertension", "Heart_Disease", "Hyperlipidemia", "Osteoarthritis", "Asthma_Copd_Bronchitis", "Cancer", "Alcohol_Drug_Abuse", "Any_Hiv_Or_Std_Related_Ailments", "Treating_Dr_Name", "Qualification", "Registration_No", "Patient_Contact_No", "Patient_Alternate_Contact_No", "Patient_Email_Id", "Patient_Alternate_Email_Id", "hypertension", "registration_no", "any_other_ailments",
        "Pre-Approval Certificate", "Pre-Auth", "Pre-Authorization", "Authorization Certificate", "Approval Certificate",
        "Estimated Expenses", "Authorized Limit", "Proposed Date Of Hospitalization", "Class Of Accommodation",
        "Estimated Expenses", "Amount Payable by Insured", "Compulsory Deduction", "Co-Payment", "Authorized Limit",
        "PAC No", "Medical Superintendent", "Ref no", "Claim", "Policy No", "ID Card Number", "Nature Of Illness",
        "Ailment", "Otolaryngology", "Proposed Date Of Hospitalization", "Estimated Duration", "Treating Doctor"
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
    
    return text

def check_keywords(text):
    """Check for category-specific keywords in the text and return the most likely category."""
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    text_lower = processed_text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}

    # Boost scores for specific document headers
    header = text_lower[:500]  # Check first 500 chars for headers
    
    # Special case for documents with both "Pre-Approval Certificate" and "Claim no"
    if (re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
        re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE)) and (
        re.search(r'\bclaim\s*no[.:]?\b', header, re.IGNORECASE) or 
        re.search(r'\bclaim\s*number\b', header, re.IGNORECASE) or
        re.search(r'\bref\s*no[.:]?\s*/\s*claim\s*no[.:]?\b', header, re.IGNORECASE)):
        category_scores["Claim Form"] += 10
        return "Claim Form"  # Prioritize claim form when both indicators are present
    
    # Check for explicit claim form indicators - highest priority
    if re.search(r'\bclaim\s*form\b', header, re.IGNORECASE):
        category_scores["Claim Form"] += 10
        return "Claim Form"  # Immediate return for explicit claim form header
    
    # Check for explicit discharge summary indicators - highest priority
    if "discharge summary" in header:
        category_scores["Discharge Summary"] += 10
        return "Discharge Summary"  # Immediate return for explicit discharge summary header
    
    # Check for explicit pre-authorization indicators - high priority
    if re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE):
        # IMPORTANT: Check if it also has explicit claim form indicators
        if re.search(r'\bclaim\s*form\b', text_lower, re.IGNORECASE):
            category_scores["Claim Form"] += 10
            return "Claim Form"  # Prioritize claim form over pre-auth
        category_scores["Pre-Auth form C"] += 10
        return "Pre-Auth form C"  # Immediate return for explicit pre-auth header
    
    # Check for explicit test report indicators in header - high priority
    if re.search(r'\btest\s*report\b', header, re.IGNORECASE) or re.search(r'\blab(oratory)?\s*report\b', header, re.IGNORECASE) or re.search(r'\bdiagnostics?\b', header, re.IGNORECASE):
        category_scores["Reports"] += 8
        # Continue checking other indicators
    
    # Check for explicit hospital bill indicators in header - high priority
    if "final bill" in header or re.search(r'\bhospital.*bill\b', header, re.IGNORECASE) or re.search(r'\bfinal.*bill\b', header, re.IGNORECASE):
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
    if re.search(r'\b(proposed|planned|estimated|expected|upcoming|scheduled)\s*(treatment|procedure|hospitalization|surgery)\b', text_lower):
        category_scores["Pre-Auth form C"] += 3
        category_scores["Claim Form"] -= 2  # Reduce claim form score
    
    # Add specific pattern detection for pre-authorization forms
    preauth_patterns = [
        r'\bpre[\s\-]*approval\b',
        r'\bpre[\s\-]*auth\b',
        r'\bpre[\s\-]*authorization\b',
        r'\bauthorization\s*certificate\b',
        r'\bapproval\s*certificate\b'
    ]
    
    preauth_matches = sum(1 for pattern in preauth_patterns if re.search(pattern, text_lower))
    if preauth_matches >= 1:
        category_scores["Pre-Auth form C"] += 6
    
    # Check for specific pre-authorization content
    if (re.search(r'\bestimated\s*expenses\b', text_lower) or 
        re.search(r'\bproposed\s*treatment\b', text_lower) or 
        re.search(r'\bauthorized\s*limit\b', text_lower)) and not re.search(r'\bfinal\s*bill\b', text_lower):
        category_scores["Pre-Auth form C"] += 4
    
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


def categorize_document(text):
    """Categorize the document based on keywords and OpenAI's API."""
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    # First, try keyword-based classification
    keyword_category = check_keywords(processed_text)
    if keyword_category:
        return keyword_category

    # Fallback to LLM if keyword check is inconclusive
    prompt = f"""You are an expert in document classification. 
    Based on the text content below (extracted from a PDF document, possibly using OCR from scanned or image-based PDFs), 
    identify which category this document belongs to from the following options:
    
    1. Claim Form (e.g., insurance or medical claim forms with fields for patient or policy details)
    2. Discharge Summary (e.g., medical summary of hospital stay, including diagnosis and treatment)
    3. Reports (e.g., medical or diagnostic reports like lab results or imaging reports)
    4. Cancelled cheque (e.g., a bank cheque marked as "CANCELLED" used for verification of bank account details, contains account number, IFSC code, MICR code, bank name, branch name)
    5. Hospital Bills (e.g., invoices or bills for medical services from hospitals)
    6. Pharmacy Bills (e.g., bills for medications and pharmacy products)
    7. Diagnostic Bills (e.g., bills for diagnostic tests and procedures)
    8. KYC (e.g., Know Your Customer documents, identity verification)
    9. Pre-Auth form C (e.g., pre-authorization forms for medical procedures, pre-approval certificates)
    10. Others (e.g., any document that does not fit the above categories)
    
    IMPORTANT RULES FOR CLASSIFICATION:
    1. If the document has "CLAIM FORM" in the header or title, it MUST be classified as "Claim Form".
    2. If the document has "CLAIM NO" or "CLAIM NUMBER" in the header, it MUST be classified as "Claim Form".
    3. Claim Forms typically include policy details, patient information, insurance details, TPA ID, and fields for reimbursement.
    4. If the document has "DISCHARGE SUMMARY" in the header or title, it MUST be classified as "Discharge Summary".
    5. Discharge Summaries typically include patient details, admission date, discharge date, diagnosis, treatment details, and follow-up notes.
    6. If the document contains "FINAL BILL" in the header or mentions "HOSPITAL" in the header along with billing information, it should be classified as "Hospital Bills".
    7. If the document lists services like "BED CHARGES", "ROOM CHARGES", "DOCTOR CONSULTANCY", "PATHOLOGICAL INVESTIGATION", "CARDIOLOGICAL INVESTIGATION", it is likely a "Hospital Bills".
    8. If the document contains "PRE-APPROVAL CERTIFICATE", "PRE-AUTH", "PRE-AUTHORIZATION" or has terms like "AUTHORIZED LIMIT", "ESTIMATED EXPENSES", "PROPOSED DATE OF HOSPITALIZATION", it should be classified as "Pre-Auth form C" UNLESS it also contains "CLAIM FORM" or "CLAIM NO" or "CLAIM NUMBER", in which case it should be classified as "Claim Form".
    9. Pre-Auth forms are issued BEFORE hospitalization and typically include estimated costs, not actual bills. They often have approval/authorization language.
    10. Only classify as "Pharmacy Bills" if the document is specifically from a pharmacy/medical store/chemist AND primarily lists medications.
    11. Hospital bills may include medicine charges as line items but should still be classified as "Hospital Bills" if they contain other hospital services.
    12. If the document contains test results, reference ranges, units of measurement (like mg/dL), and doesn't mention prices or charges, it should be classified as "Reports".
    13. Laboratory reports and diagnostic reports showing test values and reference ranges should be classified as "Reports", not as bills even if they come from a diagnostic center.
    
    The text may be noisy due to OCR, so focus on key terms, structure, or patterns that indicate the document type.
    
    Specific indicators for each category:
    - Claim Form: Look for policy details, patient information, insurance details, TPA ID, claim numbers, reimbursement information
    - Discharge Summary: Look for admission/discharge dates, diagnosis, treatment details, clinical summary, condition at discharge, follow-up advice
    - Cancelled cheque: Look for bank details like account number, IFSC code, MICR code, bank name, branch name
    - Reports: Look for test results, reference ranges, diagnostic findings, laboratory values, normal ranges, biological reference intervals, test parameters with units (like mg/dL, mmol/L), and absence of pricing information
    - Hospital Bills: Look for itemized charges for hospital services, room charges, procedure charges, consultation fees
    - Pharmacy Bills: Look for medication names, drug names, tablets, capsules, syrups, injections, prescriptions, dosage information, pharmacy/chemist/medical store names
    - Diagnostic Bills: Look for charges for specific diagnostic tests
    - Pre-Auth form C: Look for pre-approval certificate, authorization, estimated expenses, proposed treatment, authorized limit. These are issued BEFORE treatment and are NOT bills.
    
    If the document does not clearly match any of the specific categories, classify it as 'Others'.
    Respond with ONLY ONE of these category names as your answer.
    
    Document content:
    {text[:4000]}  # Limiting text to avoid token limits
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using GPT-3.5 Turbo
            temperature=0,
            messages=[
                {"role": "system", "content": "You analyze document text (which may be noisy from OCR) and classify it into exactly one of these categories: 'Claim Form', 'Discharge Summary', 'Reports', 'Cancelled cheque', 'Hospital Bills', 'Pharmacy Bills', 'Diagnostic Bills', 'KYC', 'Pre-Auth form C', or 'Others'. IMPORTANT: If the document contains 'CLAIM FORM' in the header or title, it MUST be classified as 'Claim Form'. IMPORTANT: If the document contains 'CLAIM NO' or 'CLAIM NUMBER', it MUST be classified as 'Claim Form'. Claim Forms typically include policy details, patient information, insurance details, TPA ID, and fields for reimbursement. If the document contains 'DISCHARGE SUMMARY' in the header or title, it MUST be classified as 'Discharge Summary'. Discharge summaries typically include patient details, admission date, discharge date, diagnosis, treatment details, and follow-up notes. If the document contains 'FINAL BILL' or mentions a hospital name with billing information, it should be classified as 'Hospital Bills'. Hospital bills often include services like bed charges, room charges, doctor consultancy, pathological investigation, etc. If the document contains 'PRE-APPROVAL CERTIFICATE', 'PRE-AUTH', 'PRE-AUTHORIZATION' or similar terms in the header, it should be classified as 'Pre-Auth form C' UNLESS it also contains 'CLAIM FORM' or 'CLAIM NO' or 'CLAIM NUMBER', in which case it should be classified as 'Claim Form'. Pre-Auth forms typically include estimated expenses, proposed treatment, authorized limit, and are issued before hospitalization. Only classify as 'Pharmacy Bills' if the document is specifically from a pharmacy/medical store/chemist AND primarily lists medications. Laboratory test reports showing test results with reference ranges and units (like mg/dL) should be classified as 'Reports', not as bills, even if they come from a diagnostic center or hospital laboratory. Pay special attention to bank documents - if you see bank account numbers, IFSC codes, MICR codes, or any indication of a cancelled cheque (which is a bank cheque with 'CANCELLED' written on it, used for verification of bank details), classify it as 'Cancelled cheque'. If the document does not clearly match the specific categories, return 'Others'. Respond with only the category name."},
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
                return valid_cat

        return "Others"  # Default to Others if no valid category is matched
    except Exception as e:
        return f"Error during categorization: {str(e)}"


def process_file(uploaded_file):
    """Process uploaded file based on its type."""
    file_extension = uploaded_file.name.lower().split('.')[-1]

    if file_extension == 'pdf':
        # Process PDF directly
        uploaded_file.seek(0)
        extracted_text = extract_text_from_pdf(uploaded_file)
        return extracted_text, "PDF"

    elif file_extension in ['tiff', 'tif']:
        # Convert TIFF to PDF and then process
        uploaded_file.seek(0)
        tiff_bytes = uploaded_file.read()

        # First, try direct OCR on TIFF for better quality
        extracted_text = extract_text_from_tiff(tiff_bytes)
        return extracted_text, "TIFF"

    else:
        return f"Unsupported file format: {file_extension}", "Unknown"


def main():
    st.set_page_config(
        page_title="Document Categorization App",
        page_icon="📄",
        layout="centered"
    )

    st.title("📄 Document Categorization")
    st.subheader("Automatically categorize your PDF and TIFF documents")

    st.write("""
    This application analyzes PDF and TIFF documents (including scanned or image-based files) and classifies them into one of the following categories:
    - Claim Form
    - Discharge Summary
    - Reports
    - Cancelled cheque
    - Hospital Bills
    - Pharmacy Bills
    - Diagnostic Bills
    - KYC
    - Pre-Auth form C
    - Others
    """)

    # Display file type and extension mapping
    st.markdown("**File Type and Extension Mapping:**")
    file_type_table = "| File Type | Extension |\n|---|---|\n"
    for file_type, ext in FILE_TYPE_EXTENSIONS.items():
        file_type_table += f"| {file_type} | {ext} |\n"
    st.markdown(file_type_table)

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
            extracted_text, file_type = process_file(uploaded_file)

            if extracted_text.startswith("Error") or extracted_text.startswith("Unsupported"):
                st.error(extracted_text)
            elif "No text could be extracted" in extracted_text:
                st.error(extracted_text)
            else:
                # Text extraction successful, now categorize
                with st.spinner("Categorizing document..."):
                    category = categorize_document(extracted_text)

                # Display results with nice formatting
                st.success(
                    f"Document processed successfully! (Processed as {file_type})")

                st.subheader("Document Category")
                category_color = {
                    "Claim Form": "#FF9933",
                    "Discharge Summary": "#33CC33",
                    "Reports": "#3366FF",
                    "Cancelled cheque": "#6699CC",
                    "Hospital Bills": "#CC33FF",
                    "Pharmacy Bills": "#FF6633",
                    "Diagnostic Bills": "#33CCCC",
                    "KYC": "#9966CC",
                    "Pre-Auth form C": "#FF9966",
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
                    st.text_area(
                        f"Text extracted from {file_type} (first 3 pages)",
                        extracted_text,
                        height=300
                    )


if __name__ == "__main__":
    main()
