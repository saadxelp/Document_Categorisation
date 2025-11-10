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
        "Cheque Number", "Cancelled Cheque", "Account Holder", "Bank", "Branch", "IFSC Code",
        "Cancelled", "CANCELLED", "CHEQUE", "Cheque", "Account No", "Account No.", "A/c No",
        "MICR Code", "IFSC Code", "Bank Account", "Bank Details", "Account Details",
        "Bank Branch", "Account Holder Name", "Pay to", "Pay To", "Bearer", "Order",
        "Date", "Rs", "Rupees", "Amount in words", "Signature", "Drawer", "Drawee",
        "Bank Address", "Branch Address", "Account Type", "Savings Account", "Current Account",
        "Payee", "Bearer or Order", "Cheque Leaf", "Check", "CHECK", "CHQ", "Chq No"
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


def extract_text_from_tiff_pages(tiff_file_bytes: bytes) -> list:
    """Extract text from each page of a TIFF file separately using OCR.
    Returns a list of text for each page."""
    try:
        # Open TIFF image from bytes
        image = Image.open(io.BytesIO(tiff_file_bytes))

        page_texts = []
        page_count = 0

        try:
            while True:
                # Extract text using OCR from current page
                page_text = pytesseract.image_to_string(image, lang='eng')
                if page_text and page_text.strip():
                    page_texts.append(page_text)
                else:
                    page_texts.append("")  # Add empty string for pages with no text

                page_count += 1
                try:
                    image.seek(page_count)
                except EOFError:
                    # End of pages reached
                    break
        except EOFError:
            # Single page TIFF or end of pages - already processed
            if not page_texts:
                # If no pages were processed, it's a single page
                page_text = pytesseract.image_to_string(image, lang='eng')
                if page_text and page_text.strip():
                    page_texts.append(page_text)
                else:
                    page_texts.append("")

        return page_texts if page_texts else ["No text could be extracted from the TIFF file."]
    except Exception as e:
        return [f"Error extracting text from TIFF: {str(e)}"]


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
    
    # ========== CRITICAL: OCR ERROR CORRECTIONS FOR CANCELLED CHEQUES ==========
    # Common OCR errors in cancelled cheques - CRITICAL for proper detection
    text = text.replace('CAN( ELLED', 'CANCELLED')
    text = text.replace('CANCELIED', 'CANCELLED')
    text = text.replace('CANCEILED', 'CANCELLED')
    text = text.replace('CH EQUE', 'CHEQUE')
    text = text.replace('CHE OU E', 'CHEQUE')
    text = text.replace('CHEQU E', 'CHEQUE')
    text = text.replace('CH ECK', 'CHECK')
    text = text.replace('A /C', 'A/C')
    text = text.replace('A/ C', 'A/C')
    text = text.replace('ACCOUNT N0', 'ACCOUNT NO')
    text = text.replace('ACCO UNT', 'ACCOUNT')
    text = text.replace('IFS CODE', 'IFSC CODE')  # Common OCR error: IFS vs IFSC
    text = text.replace('IFS C', 'IFSC')
    
    # Fix spacing around cheque terms
    text = re.sub(r'CAN\s*CEL\s*LED', 'CANCELLED', text, flags=re.IGNORECASE)
    text = re.sub(r'CAN\s*CELED', 'CANCELLED', text, flags=re.IGNORECASE)
    text = re.sub(r'CAN\s*CELLED', 'CANCELLED', text, flags=re.IGNORECASE)
    text = re.sub(r'CHE\s*QUE', 'CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'CH\s*EQ\s*UE', 'CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'CANCELLED\s*CHEQUE', 'CANCELLED CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'CANCELLED\s*CHECK', 'CANCELLED CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'CANCELLED\s*CHQ', 'CANCELLED CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'AC\s*COUNT\s*NO', 'ACCOUNT NO', text, flags=re.IGNORECASE)
    text = re.sub(r'A\s*/\s*C\s*NO', 'A/C NO', text, flags=re.IGNORECASE)
    text = re.sub(r'A\s*/\s*C', 'A/C', text, flags=re.IGNORECASE)
    text = re.sub(r'IFS\s*C\s*ODE', 'IFSC CODE', text, flags=re.IGNORECASE)
    text = re.sub(r'IFS\s*C', 'IFSC', text, flags=re.IGNORECASE)
    text = re.sub(r'MIC\s*R', 'MICR', text, flags=re.IGNORECASE)
    text = re.sub(r'PAY\s*TO', 'PAY TO', text, flags=re.IGNORECASE)
    text = re.sub(r'PAY\s*SELF', 'PAY SELF', text, flags=re.IGNORECASE)
    text = re.sub(r'BE\s*ARER', 'BEARER', text, flags=re.IGNORECASE)
    text = re.sub(r'OR\s*DER', 'ORDER', text, flags=re.IGNORECASE)
    text = re.sub(r'RU\s*PEES', 'RUPEES', text, flags=re.IGNORECASE)
    text = re.sub(r'MULTI\s*[\-\s]*CITY\s*CHEQUE', 'MULTI-CITY CHEQUE', text, flags=re.IGNORECASE)
    text = re.sub(r'VALID\s*FOR\s*(\d+)\s*MONTHS?', 'VALID FOR MONTHS', text, flags=re.IGNORECASE)
    
    return text

def check_keywords(text):
    """Check for category-specific keywords in the text and return the most likely category."""
    # Preprocess text for better header detection
    processed_text = preprocess_text_for_header_detection(text)
    
    text_lower = processed_text.lower()
    category_scores = {category: 0 for category in CATEGORY_KEYWORDS}

    # Boost scores for specific document headers
    header = text_lower[:500]  # Check first 500 chars for headers
    
    # ========== CRITICAL: CANCELLED CHEQUE DETECTION - HIGHEST PRIORITY ==========
    # This MUST be checked FIRST before any other category to prevent misclassification
    
    # Pattern 1: Explicit "CANCELLED CHEQUE" text anywhere in document
    if (re.search(r'\b(cancelled|canceled)\s*(cheque|check|chq)\b', text_lower, re.IGNORECASE) or 
        re.search(r'\b(cheque|check|chq)\s*(cancelled|canceled)\b', text_lower, re.IGNORECASE)):
        return "Cancelled cheque"
    
    # Pattern 2: Cheque structure indicators (PAY, PAY TO, PAY SELF, BEARER, ORDER) + Account number + Bank details
    # This is the MOST COMMON pattern for cheques (even without "CANCELLED" text)
    has_pay_structure = re.search(r'\b(pay\s*(to|self|to the order of)|bearer|order|drawee|drawer)\b', text_lower, re.IGNORECASE)
    has_account = re.search(r'\b(account\s*(no|number|#)|a[\/\s]*c\s*(no|number|#))\s*[:]?\s*[0-9]+\b', text_lower, re.IGNORECASE)
    has_bank_details = re.search(r'\b(ifsc|ifs\s*c|micr|bank|branch)\s*(code|number|name)?\s*[:]?\s*[A-Z0-9]+\b', text_lower, re.IGNORECASE)
    no_medical_terms = not re.search(r'\b(bill|invoice|charge|patient|hospital|medical|treatment|diagnosis|gst|tax|consultation|room|bed|final\s*bill)\b', text_lower, re.IGNORECASE)
    
    if has_pay_structure and has_account and has_bank_details and no_medical_terms:
        return "Cancelled cheque"  # Strong cheque structure match
    
    # Pattern 3: IFSC/MICR code + Account number pattern (even without PAY structure)
    # IFSC format: 4 letters + 0 + 6 alphanumeric (e.g., SBIN0011724, HDFC0001234)
    # MICR format: 9 digits typically
    ifsc_pattern = re.search(r'\b(ifsc|ifs\s*c)\s*(code|number)?\s*[:]?\s*([A-Z]{4}0[A-Z0-9]{6,})\b', text_lower, re.IGNORECASE)
    micr_pattern = re.search(r'\bmicr\s*(code|number)?\s*[:]?\s*([0-9]{6,})\b', text_lower, re.IGNORECASE)
    account_pattern = re.search(r'\b(account\s*(no|number|#)|a[\/\s]*c\s*(no|number|#))\s*[:]?\s*([0-9]{6,})\b', text_lower, re.IGNORECASE)
    
    if (ifsc_pattern or micr_pattern) and account_pattern and no_medical_terms:
        return "Cancelled cheque"  # IFSC/MICR + Account number = Cheque
    
    # Pattern 4: Cheque-specific keywords combination
    # "RUPEES" + Amount in words/figures + Account number + Bank details
    has_rupees = re.search(r'\brupees?\b', text_lower, re.IGNORECASE)
    has_amount = re.search(r'\b(ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|crore)\s*(rupees?|only)\b', text_lower, re.IGNORECASE)
    has_currency_symbol = re.search(r'₹|Rs\.?|INR', text_lower, re.IGNORECASE)
    
    if (has_rupees or has_amount or has_currency_symbol) and has_account and has_bank_details and no_medical_terms:
        return "Cancelled cheque"  # Currency/amount indicators + account + bank = Cheque
    
    # Pattern 5: MULTI-CITY CHEQUE or VALID FOR X MONTHS (cheque-specific text)
    if (re.search(r'\b(multi[\s\-]*city|valid\s*for\s*\d+\s*months?|cheque\s*leaf|please\s*sign)\b', text_lower, re.IGNORECASE) and 
        has_account and no_medical_terms):
        return "Cancelled cheque"  # Cheque-specific terminology
    
    # Pattern 6: Date field pattern (DDMMYYYY) + Account number + Bank (cheque structure)
    # Cheques typically have date fields like "D D M M Y Y Y Y"
    if (re.search(r'\b([0-9]{1,2}\s*[0-9]{1,2}\s*[0-9]{4}|d\s*d\s*m\s*m\s*y\s*y\s*y\s*y|date)\b', text_lower, re.IGNORECASE) and
        has_account and has_bank_details and no_medical_terms):
        return "Cancelled cheque"  # Date field + account + bank = Cheque structure
    
    # Special case for Pre-Auth forms - they should be prioritized even if they contain claim numbers
    if (re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
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
    if re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*auth\b', header, re.IGNORECASE) or re.search(r'\bpre[\s\-]*authorization\b', header, re.IGNORECASE) or re.search(r'\brequest\s*for\s*cash\s*less\s*hospitali[sz]ation\b', header, re.IGNORECASE):
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
        
    # Special patterns for cancelled cheques - HIGH PRIORITY
    # Check for explicit cancelled cheque indicators
    if re.search(r'\b(cancelled|canceled)\s*(cheque|check|chq)\b', text_lower, re.IGNORECASE) or re.search(r'\b(cheque|check|chq)\s*(cancelled|canceled)\b', text_lower, re.IGNORECASE):
        category_scores["Cancelled cheque"] += 10
        category_scores["Hospital Bills"] -= 5  # Reduce hospital bills score
    
    # Check for cheque leaf pattern (physical cheque structure)
    if (re.search(r'\b(pay\s*(to|to the)|bearer|order|drawee|drawer)\b', text_lower) and 
        re.search(r'\b(account\s*(no|number|#)|a\/c\s*(no|number))\b', text_lower) and
        re.search(r'\b(ifsc|micr|bank|branch)\b', text_lower)):
        category_scores["Cancelled cheque"] += 8
        category_scores["Hospital Bills"] -= 4  # Reduce hospital bills score
    
    # Strong bank account indicators with cheque context
    if (re.search(r'\b(ifsc|micr)\s*(code|number)\b', text_lower) and 
        (re.search(r'\baccount\s*(no|number|#|holder)\b', text_lower) or 
         re.search(r'\ba\/c\s*(no|number)\b', text_lower)) and
        not re.search(r'\b(bill|invoice|charge|payment due|gst|tax)\b', text_lower)):
        category_scores["Cancelled cheque"] += 7
        category_scores["Hospital Bills"] -= 3  # Reduce hospital bills score
    
    # Cheque number with bank details (no bill/invoice context)
    if (re.search(r'\b(cheque|check|chq)\s*(no|number|#)\b', text_lower) and
        re.search(r'\b(bank|branch|ifsc|micr)\b', text_lower) and
        not re.search(r'\b(final|bill|invoice|patient|hospital)\b', text_lower)):
        category_scores["Cancelled cheque"] += 6
        category_scores["Hospital Bills"] -= 3  # Reduce hospital bills score
    
    # Account number with bank name but no medical/billing terms
    if (re.search(r'\baccount\s*(no|number|#)\b', text_lower) and 
        re.search(r'\b(bank|branch|ifsc|micr)\b', text_lower) and
        not re.search(r'\b(bill|invoice|charge|patient|hospital|medical|treatment|diagnosis)\b', text_lower)):
        category_scores["Cancelled cheque"] += 4
    
    # Basic cheque indicators
    if "cheque" in text_lower or "check" in text_lower or re.search(r'\bchq\b', text_lower):
        category_scores["Cancelled cheque"] += 2
    
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
    prompt = f"""You are an expert in document classification. 
    Based on the text content below (extracted from a single page of a PDF document, possibly using OCR from scanned or image-based PDFs), 
    identify which category this document page belongs to from the following options:
    
    1. Claim Form (e.g., insurance or medical claim forms with fields for patient or policy details)
    2. Discharge Summary (e.g., medical summary of hospital stay, including diagnosis and treatment)
    3. Reports (e.g., medical or diagnostic reports like lab results or imaging reports)
    4. Cancelled cheque (e.g., a bank cheque marked as "CANCELLED" used for verification of bank account details, contains account number, IFSC code, MICR code, bank name, branch name, cheque structure with "PAY", "BEARER", "ORDER", "RUPEES")
    5. Hospital Bills (e.g., invoices or bills for medical services from hospitals)
    6. Pharmacy Bills (e.g., bills for medications and pharmacy products)
    7. Diagnostic Bills (e.g., bills for diagnostic tests and procedures)
    8. KYC (e.g., Know Your Customer documents, identity verification)
    9. Pre-Auth form C (e.g., pre-authorization forms for medical procedures, pre-approval certificates)
    10. Others (e.g., any document that does not fit the above categories)
    
    ⚠️⚠️⚠️ CRITICAL: YOU MUST CHECK FOR CANCELLED CHEQUE FIRST ⚠️⚠️⚠️
    ⚠️⚠️⚠️ THIS IS THE HIGHEST PRIORITY - CHECK BEFORE ALL OTHER CATEGORIES ⚠️⚠️⚠️
    
    ========== STEP 1: CANCELLED CHEQUE DETECTION (MANDATORY FIRST STEP) ==========
    
    A document is "Cancelled cheque" if ANY of these patterns are found:
    
    ✅ PATTERN 1: Explicit cancelled cheque text
       - Text contains "CANCELLED CHEQUE" OR "CANCELLED CHECK" OR "CANCELED CHEQUE"
       - OR words "CANCELLED" + "CHEQUE/CHECK/CHQ" appear together
       → IMMEDIATELY answer: "Cancelled cheque" (STOP - do not check other categories)
    
    ✅ PATTERN 2: Cheque payment structure (MOST COMMON - works even without "CANCELLED" word)
       - Contains: "PAY" OR "PAY TO" OR "PAY SELF" OR "PAY TO THE ORDER OF"
       - AND contains: "BEARER" OR "ORDER" OR "OR ORDER"
       - AND contains: Account number (A/C No, A/C Number, Account No, Account Number with digits)
       - AND contains: IFSC code (format like SBIN0011724, HDFC0001234) OR MICR code (9+ digits) OR Bank name OR Branch name
       - AND DOES NOT contain: "patient", "hospital", "bill", "invoice", "charge", "medical", "treatment", "GST", "tax"
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 3: IFSC/MICR code + Account number (STRONG INDICATOR)
       - Contains: IFSC code (4 letters + 0 + 6 alphanumeric, e.g., "SBIN0011724", "HDFC0001234", "IFSC: SBIN0011724")
       - OR contains: MICR code (9+ digits, e.g., "695002032", "MICR: 123456789")
       - AND contains: Account number (A/C No, Account No with 6+ digits, e.g., "00001234556001")
       - AND DOES NOT contain: "bill", "invoice", "patient", "hospital", "medical", "treatment", "charge", "GST", "tax"
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 4: Currency/Amount indicators + Account + Bank
       - Contains: "RUPEES" OR amount in words ("Ten thousand rupees only", "Hundred rupees")
       - OR contains: Currency symbol (₹, Rs., INR, ₹10,000)
       - AND contains: Account number
       - AND contains: Bank details (IFSC/MICR/Bank name/Branch)
       - AND DOES NOT contain medical/billing terms
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 5: Cheque-specific terminology
       - Contains: "MULTI-CITY CHEQUE" OR "VALID FOR 3 MONTHS" OR "VALID FOR X MONTHS" OR "CHEQUE LEAF" OR "PLEASE SIGN"
       - AND contains: Account number
       - AND DOES NOT contain medical/billing terms
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ⚠️ CRITICAL DISTINCTION: Cancelled cheque vs Hospital Bills ⚠️
    - IF you see: "PAY" + Account number + IFSC/MICR + NO "patient"/"hospital"/"bill"/"invoice" → "Cancelled cheque"
    - IF you see: "FINAL BILL" + Account number + "patient"/"hospital"/"charges"/"GST" → "Hospital Bills"
    - KEY RULE: Bank account details (IFSC/MICR + Account) WITHOUT medical/billing context = "Cancelled cheque"
    
    ❌ ONLY IF NONE OF THE ABOVE PATTERNS MATCH, THEN PROCEED TO STEP 2:
    
    ========== STEP 2: OTHER CATEGORY CHECKS ==========
    1. HEADER-BASED CLASSIFICATION:
       - If "PRE-APPROVAL CERTIFICATE", "PRE-AUTH", "PRE-AUTHORIZATION", "REQUEST FOR CASHLESS HOSPITALIZATION" in header → "Pre-Auth form C" (HIGHEST PRIORITY)
       - If "CLAIM FORM" appears in header/title → "Claim Form"
       - If "CLAIM NO" or "CLAIM NUMBER" appears anywhere in document → "Claim Form" (IMPORTANT: This overrides other classifications)
       - If "DISCHARGE SUMMARY" appears in header/title → "Discharge Summary"  
       - If "CENTRAL KYC REGISTRY", "CERSAI", "KYC APPLICATION FORM", "KNOW YOUR CUSTOMER" in header → "KYC"
       - If "FINAL BILL" or hospital name with billing info in header → "Hospital Bills"
       - If "TEST REPORT", "LAB REPORT", "DIAGNOSTICS" in header → "Reports"
       - If "PHARMACY", "MEDICAL STORE", "CHEMIST" in header → "Pharmacy Bills"
    
    2. CONTENT-BASED CLASSIFICATION:
       - CANCELLED CHEQUE (VERY IMPORTANT - Distinguish from Hospital Bills):
         * Physical cheque structure: "PAY TO", "BEARER", "ORDER", "DRAWER", "DRAWEE"
         * Bank details: Account number (A/C No, Account No), IFSC code, MICR code, Bank name, Branch name
         * Cheque-specific fields: Cheque number, Date field, Amount in words, Signature section
         * NO medical terms: Should NOT contain "patient", "hospital", "bill", "invoice", "charge", "medical", "treatment", "diagnosis"
         * If you see "IFSC" or "MICR" code + Account number but NO medical/billing terms → "Cancelled cheque"
         * If you see cheque structure (Pay to/Bearer/Order) + bank account details → "Cancelled cheque"
       - Pre-Auth forms: Estimated expenses, proposed treatment, authorized limit, BEFORE hospitalization language, "TO BE FILLED BY INSURED", future tense (proposed, planned, estimated, expected)
       - Claim Forms: Policy details, patient info, insurance details, TPA ID, claim numbers (CLAIM NO/CLAIM NUMBER), reimbursement fields, past tense (incurred, spent, paid, underwent)
       - Discharge Summaries: Admission/discharge dates, diagnosis, treatment details, clinical summary, follow-up advice
       - Hospital Bills: Itemized charges for hospital services, room charges, procedure charges, consultation fees, patient information, GST/tax information, bill numbers
       - Pharmacy Bills: Medication names, drug names, tablets, capsules, syrups, prescriptions, dosage info
       - Reports: Test results, reference ranges, diagnostic findings, laboratory values, units (mg/dL, mmol/L), NO pricing
       - KYC: Personal details, identity/address sections, customer info, photograph/signature fields
    
    3. CONTEXT CLUES (CRITICAL DISTINCTIONS):
       - CANCELLED CHEQUE vs HOSPITAL BILLS:
         * Cancelled cheque: Has IFSC/MICR code + Account number BUT NO "bill", "invoice", "patient", "hospital", "medical", "treatment", "charge", "GST", "tax" → "Cancelled cheque"
         * Cancelled cheque: Has cheque structure ("Pay to", "Bearer", "Order") + bank details → "Cancelled cheque"
         * Hospital Bills: Has billing information, charges, patient details, medical services, GST/tax → "Hospital Bills"
         * If document has bank account number + IFSC/MICR but NO medical/billing context → "Cancelled cheque" (NOT Hospital Bills)
       - Future tense (proposed, planned, estimated, expected) + "TO BE FILLED BY INSURED" → Pre-Auth form C (HIGHEST PRIORITY)
       - Past tense (incurred, spent, paid, underwent) → Claim Form
       - Presence of "CLAIM NO" or "CLAIM NUMBER" anywhere in document → Claim Form (IMPORTANT: This overrides other classifications)
       - Test values with units but no prices → Reports
       - Service charges with prices → Hospital Bills
       - Medication lists with prices → Pharmacy Bills
    
    4. DOCUMENT BOUNDARY DETECTION:
       - Each page should be classified independently based on its own content
       - Do NOT assume continuity from previous pages
       - Look for clear document headers and content indicators on each individual page
       - If a page has "CLAIM FORM" in the header, it should be classified as "Claim Form" regardless of what the previous page was
    
    IMPORTANT: Focus on the MOST PROMINENT document type indicators on THIS SPECIFIC PAGE. If multiple types are present, prioritize based on header information first, then content density. Each page is a separate document that should be classified independently.
    
    Respond with ONLY the category name.
    
    Document content:
    {processed_text[:4000]}
    """

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
    prompt = f"""You are an expert in document classification. 
    Based on the text content below (extracted from a single page of a PDF document, possibly using OCR from scanned or image-based PDFs), 
    identify which category this document page belongs to from the following options:
    
    1. Claim Form (e.g., insurance or medical claim forms with fields for patient or policy details)
    2. Discharge Summary (e.g., medical summary of hospital stay, including diagnosis and treatment)
    3. Reports (e.g., medical or diagnostic reports like lab results or imaging reports)
    4. Cancelled cheque (e.g., a bank cheque marked as "CANCELLED" used for verification of bank account details, contains account number, IFSC code, MICR code, bank name, branch name, cheque structure with "PAY", "BEARER", "ORDER", "RUPEES")
    5. Hospital Bills (e.g., invoices or bills for medical services from hospitals)
    6. Pharmacy Bills (e.g., bills for medications and pharmacy products)
    7. Diagnostic Bills (e.g., bills for diagnostic tests and procedures)
    8. KYC (e.g., Know Your Customer documents, identity verification)
    9. Pre-Auth form C (e.g., pre-authorization forms for medical procedures, pre-approval certificates)
    10. Others (e.g., any document that does not fit the above categories)
    
    ⚠️⚠️⚠️ CRITICAL: YOU MUST CHECK FOR CANCELLED CHEQUE FIRST ⚠️⚠️⚠️
    ⚠️⚠️⚠️ THIS IS THE HIGHEST PRIORITY - CHECK BEFORE ALL OTHER CATEGORIES ⚠️⚠️⚠️
    
    ========== STEP 1: CANCELLED CHEQUE DETECTION (MANDATORY FIRST STEP) ==========
    
    A document is "Cancelled cheque" if ANY of these patterns are found:
    
    ✅ PATTERN 1: Explicit cancelled cheque text
       - Text contains "CANCELLED CHEQUE" OR "CANCELLED CHECK" OR "CANCELED CHEQUE"
       - OR words "CANCELLED" + "CHEQUE/CHECK/CHQ" appear together
       → IMMEDIATELY answer: "Cancelled cheque" (STOP - do not check other categories)
    
    ✅ PATTERN 2: Cheque payment structure (MOST COMMON - works even without "CANCELLED" word)
       - Contains: "PAY" OR "PAY TO" OR "PAY SELF" OR "PAY TO THE ORDER OF"
       - AND contains: "BEARER" OR "ORDER" OR "OR ORDER"
       - AND contains: Account number (A/C No, A/C Number, Account No, Account Number with digits)
       - AND contains: IFSC code (format like SBIN0011724, HDFC0001234) OR MICR code (9+ digits) OR Bank name OR Branch name
       - AND DOES NOT contain: "patient", "hospital", "bill", "invoice", "charge", "medical", "treatment", "GST", "tax"
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 3: IFSC/MICR code + Account number (STRONG INDICATOR)
       - Contains: IFSC code (4 letters + 0 + 6 alphanumeric, e.g., "SBIN0011724", "HDFC0001234", "IFSC: SBIN0011724")
       - OR contains: MICR code (9+ digits, e.g., "695002032", "MICR: 123456789")
       - AND contains: Account number (A/C No, Account No with 6+ digits, e.g., "00001234556001")
       - AND DOES NOT contain: "bill", "invoice", "patient", "hospital", "medical", "treatment", "charge", "GST", "tax"
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 4: Currency/Amount indicators + Account + Bank
       - Contains: "RUPEES" OR amount in words ("Ten thousand rupees only", "Hundred rupees")
       - OR contains: Currency symbol (₹, Rs., INR, ₹10,000)
       - AND contains: Account number
       - AND contains: Bank details (IFSC/MICR/Bank name/Branch)
       - AND DOES NOT contain medical/billing terms
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ✅ PATTERN 5: Cheque-specific terminology
       - Contains: "MULTI-CITY CHEQUE" OR "VALID FOR 3 MONTHS" OR "VALID FOR X MONTHS" OR "CHEQUE LEAF" OR "PLEASE SIGN"
       - AND contains: Account number
       - AND DOES NOT contain medical/billing terms
       → IMMEDIATELY answer: "Cancelled cheque"
    
    ⚠️ CRITICAL DISTINCTION: Cancelled cheque vs Hospital Bills ⚠️
    - IF you see: "PAY" + Account number + IFSC/MICR + NO "patient"/"hospital"/"bill"/"invoice" → "Cancelled cheque"
    - IF you see: "FINAL BILL" + Account number + "patient"/"hospital"/"charges"/"GST" → "Hospital Bills"
    - KEY RULE: Bank account details (IFSC/MICR + Account) WITHOUT medical/billing context = "Cancelled cheque"
    
    ❌ ONLY IF NONE OF THE ABOVE PATTERNS MATCH, THEN PROCEED TO STEP 2:
    
    ========== STEP 2: OTHER CATEGORY CHECKS ==========
    1. HEADER-BASED CLASSIFICATION:
       - If "PRE-APPROVAL CERTIFICATE", "PRE-AUTH", "PRE-AUTHORIZATION", "REQUEST FOR CASHLESS HOSPITALIZATION" in header → "Pre-Auth form C" (HIGHEST PRIORITY)
       - If "CLAIM FORM" appears in header/title → "Claim Form"
       - If "CLAIM NO" or "CLAIM NUMBER" appears anywhere in document → "Claim Form" (IMPORTANT: This overrides other classifications)
       - If "DISCHARGE SUMMARY" appears in header/title → "Discharge Summary"  
       - If "CENTRAL KYC REGISTRY", "CERSAI", "KYC APPLICATION FORM", "KNOW YOUR CUSTOMER" in header → "KYC"
       - If "FINAL BILL" or hospital name with billing info in header → "Hospital Bills"
       - If "TEST REPORT", "LAB REPORT", "DIAGNOSTICS" in header → "Reports"
       - If "PHARMACY", "MEDICAL STORE", "CHEMIST" in header → "Pharmacy Bills"
    
    2. CONTENT-BASED CLASSIFICATION:
       - CANCELLED CHEQUE (VERY IMPORTANT - Distinguish from Hospital Bills):
         * Physical cheque structure: "PAY TO", "BEARER", "ORDER", "DRAWER", "DRAWEE"
         * Bank details: Account number (A/C No, Account No), IFSC code, MICR code, Bank name, Branch name
         * Cheque-specific fields: Cheque number, Date field, Amount in words, Signature section
         * NO medical terms: Should NOT contain "patient", "hospital", "bill", "invoice", "charge", "medical", "treatment", "diagnosis"
         * If you see "IFSC" or "MICR" code + Account number but NO medical/billing terms → "Cancelled cheque"
         * If you see cheque structure (Pay to/Bearer/Order) + bank account details → "Cancelled cheque"
       - Pre-Auth forms: Estimated expenses, proposed treatment, authorized limit, BEFORE hospitalization language, "TO BE FILLED BY INSURED", future tense (proposed, planned, estimated, expected)
       - Claim Forms: Policy details, patient info, insurance details, TPA ID, claim numbers (CLAIM NO/CLAIM NUMBER), reimbursement fields, past tense (incurred, spent, paid, underwent)
       - Discharge Summaries: Admission/discharge dates, diagnosis, treatment details, clinical summary, follow-up advice
       - Hospital Bills: Itemized charges for hospital services, room charges, procedure charges, consultation fees, patient information, GST/tax information, bill numbers
       - Pharmacy Bills: Medication names, drug names, tablets, capsules, syrups, prescriptions, dosage info
       - Reports: Test results, reference ranges, diagnostic findings, laboratory values, units (mg/dL, mmol/L), NO pricing
       - KYC: Personal details, identity/address sections, customer info, photograph/signature fields
    
    3. CONTEXT CLUES (CRITICAL DISTINCTIONS):
       - CANCELLED CHEQUE vs HOSPITAL BILLS:
         * Cancelled cheque: Has IFSC/MICR code + Account number BUT NO "bill", "invoice", "patient", "hospital", "medical", "treatment", "charge", "GST", "tax" → "Cancelled cheque"
         * Cancelled cheque: Has cheque structure ("Pay to", "Bearer", "Order") + bank details → "Cancelled cheque"
         * Hospital Bills: Has billing information, charges, patient details, medical services, GST/tax → "Hospital Bills"
         * If document has bank account number + IFSC/MICR but NO medical/billing context → "Cancelled cheque" (NOT Hospital Bills)
       - Future tense (proposed, planned, estimated, expected) + "TO BE FILLED BY INSURED" → Pre-Auth form C (HIGHEST PRIORITY)
       - Past tense (incurred, spent, paid, underwent) → Claim Form
       - Presence of "CLAIM NO" or "CLAIM NUMBER" anywhere in document → Claim Form (IMPORTANT: This overrides other classifications)
       - Test values with units but no prices → Reports
       - Service charges with prices → Hospital Bills
       - Medication lists with prices → Pharmacy Bills
    
    4. DOCUMENT BOUNDARY DETECTION:
       - Each page should be classified independently based on its own content
       - Do NOT assume continuity from previous pages
       - Look for clear document headers and content indicators on each individual page
       - If a page has "CLAIM FORM" in the header, it should be classified as "Claim Form" regardless of what the previous page was
    
    IMPORTANT: Focus on the MOST PROMINENT document type indicators on THIS SPECIFIC PAGE. If multiple types are present, prioritize based on header information first, then content density. Each page is a separate document that should be classified independently.
    
    Respond with ONLY the category name.
    
    Document content:
    {processed_text[:4000]}
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": "⚠️⚠️⚠️ CRITICAL INSTRUCTIONS ⚠️⚠️⚠️\n\nYou are a document classification expert. You MUST check for 'Cancelled cheque' FIRST before any other category.\n\nSTEP 1 - Check for Cancelled Cheque (MANDATORY FIRST):\n✅ If text contains 'CANCELLED CHEQUE' or 'CANCELLED CHECK' → Answer: 'Cancelled cheque'\n✅ If text contains 'PAY'/'PAY TO'/'PAY SELF' + Account number + IFSC/MICR/Bank + NO medical terms → Answer: 'Cancelled cheque'\n✅ If text contains IFSC code (format: 4 letters + 0 + 6 alphanumeric like SBIN0011724) + Account number + NO medical/billing terms → Answer: 'Cancelled cheque'\n✅ If text contains MICR code (9+ digits) + Account number + NO medical/billing terms → Answer: 'Cancelled cheque'\n✅ If text contains 'RUPEES' + Account number + Bank details + NO medical terms → Answer: 'Cancelled cheque'\n✅ If text contains 'MULTI-CITY CHEQUE' or 'VALID FOR X MONTHS' + Account number + NO medical terms → Answer: 'Cancelled cheque'\n\nSTEP 2 - Only if NOT a cancelled cheque, classify into: 'Claim Form', 'Discharge Summary', 'Reports', 'Hospital Bills', 'Pharmacy Bills', 'Diagnostic Bills', 'KYC', 'Pre-Auth form C', or 'Others'\n\n⚠️ REMEMBER: Documents with IFSC/MICR + Account number but WITHOUT medical/billing context are ALWAYS 'Cancelled cheque', NOT 'Hospital Bills'!\n\nRespond with ONLY the category name."},
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
    
    # Strong header indicators (confidence 0.9-1.0)
    if re.search(r'\bclaim\s*form\b', header, re.IGNORECASE):
        return {'category': "Claim Form", 'confidence': 1.0}
    
    # Check for "Claim No" indicator - highest priority for claim forms
    if re.search(r'\bclaim\s*no[.:]?\b', text_lower, re.IGNORECASE):
        return {'category': "Claim Form", 'confidence': 1.0}
    
    # ========== CRITICAL: CANCELLED CHEQUE DETECTION - HIGHEST PRIORITY ==========
    # Pattern 1: Explicit cancelled cheque text
    if (re.search(r'\b(cancelled|canceled)\s*(cheque|check|chq)\b', text_lower, re.IGNORECASE) or 
        re.search(r'\b(cheque|check|chq)\s*(cancelled|canceled)\b', text_lower, re.IGNORECASE)):
        return {'category': "Cancelled cheque", 'confidence': 1.0}
    
    # Pattern 2: Cheque payment structure (PAY + Account + Bank details)
    has_pay_structure = re.search(r'\b(pay\s*(to|self|to the order of)|bearer|order|drawee|drawer)\b', text_lower, re.IGNORECASE)
    has_account = re.search(r'\b(account\s*(no|number|#)|a[\/\s]*c\s*(no|number|#))\s*[:]?\s*[0-9]+\b', text_lower, re.IGNORECASE)
    has_bank_details = re.search(r'\b(ifsc|ifs\s*c|micr|bank|branch)\s*(code|number|name)?\s*[:]?\s*[A-Z0-9]+\b', text_lower, re.IGNORECASE)
    no_medical_terms = not re.search(r'\b(bill|invoice|charge|patient|hospital|medical|treatment|diagnosis|gst|tax|consultation|room|bed|final\s*bill)\b', text_lower, re.IGNORECASE)
    
    if has_pay_structure and has_account and has_bank_details and no_medical_terms:
        return {'category': "Cancelled cheque", 'confidence': 1.0}
    
    # Pattern 3: IFSC/MICR code + Account number pattern
    ifsc_pattern = re.search(r'\b(ifsc|ifs\s*c)\s*(code|number)?\s*[:]?\s*([A-Z]{4}0[A-Z0-9]{6,})\b', text_lower, re.IGNORECASE)
    micr_pattern = re.search(r'\bmicr\s*(code|number)?\s*[:]?\s*([0-9]{6,})\b', text_lower, re.IGNORECASE)
    account_pattern = re.search(r'\b(account\s*(no|number|#)|a[\/\s]*c\s*(no|number|#))\s*[:]?\s*([0-9]{6,})\b', text_lower, re.IGNORECASE)
    
    if (ifsc_pattern or micr_pattern) and account_pattern and no_medical_terms:
        return {'category': "Cancelled cheque", 'confidence': 1.0}
    
    # Pattern 4: Currency/Amount indicators + Account + Bank
    has_rupees = re.search(r'\brupees?\b', text_lower, re.IGNORECASE)
    has_amount = re.search(r'\b(ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|crore)\s*(rupees?|only)\b', text_lower, re.IGNORECASE)
    has_currency_symbol = re.search(r'₹|Rs\.?|INR', text_lower, re.IGNORECASE)
    
    if (has_rupees or has_amount or has_currency_symbol) and has_account and has_bank_details and no_medical_terms:
        return {'category': "Cancelled cheque", 'confidence': 1.0}
    
    # Pattern 5: Cheque-specific terminology
    if (re.search(r'\b(multi[\s\-]*city|valid\s*for\s*\d+\s*months?|cheque\s*leaf|please\s*sign)\b', text_lower, re.IGNORECASE) and 
        has_account and no_medical_terms):
        return {'category': "Cancelled cheque", 'confidence': 1.0}
    
    if "discharge summary" in header:
        return {'category': "Discharge Summary", 'confidence': 1.0}
    
    if re.search(r'\bcentral\s*kyc\s*registry\b', header, re.IGNORECASE) or re.search(r'\bcersai\b', header, re.IGNORECASE):
        return {'category': "KYC", 'confidence': 1.0}
    
    if (re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
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
    
    # Group consecutive pages with the same category
    grouped_results = []
    current_category = page_categories[0]
    start_page = 1
    end_page = 1
    
    for i in range(1, len(page_categories)):
        if page_categories[i] == current_category:
            end_page = i + 1
        else:
            # Add the current group
            if start_page == end_page:
                grouped_results.append(f"Page {start_page}: {current_category}")
            else:
                grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
            
            # Start new group
            current_category = page_categories[i]
            start_page = i + 1
            end_page = i + 1
    
    # Add the last group
    if start_page == end_page:
        grouped_results.append(f"Page {start_page}: {current_category}")
    else:
        grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
    
    return grouped_results, page_categories


def check_explicit_document_indicators(page_text, current_category, confidence):
    """Check for explicit document type indicators that override continuity logic."""
    if not page_text or page_text.startswith("Error") or "No text could be extracted" in page_text:
        return current_category
    
    text_lower = page_text.lower()
    header = text_lower[:500]  # Check first 500 chars for headers
    
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
    
    if (re.search(r'\bpre[\s\-]*approval\s*certificate\b', header, re.IGNORECASE) or 
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
        
        # High confidence results (0.8+) are kept as-is
        if confidence >= 0.8:
            final_categories.append(category)
            continue
        
        # Check if this page has strong indicators for a specific document type
        explicit_category = check_explicit_document_indicators(page_text, category, confidence)
        if explicit_category and explicit_category != category:
            final_categories.append(explicit_category)
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


def process_file(uploaded_file):
    """Process uploaded file based on its type."""
    file_extension = uploaded_file.name.lower().split('.')[-1]

    if file_extension == 'pdf':
        # Process PDF directly - now returns list of page texts
        uploaded_file.seek(0)
        page_texts = extract_text_from_pdf(uploaded_file)
        return page_texts, "PDF"

    elif file_extension in ['tiff', 'tif']:
        # Extract text from each page of TIFF separately
        uploaded_file.seek(0)
        tiff_bytes = uploaded_file.read()

        # Extract text from each page separately
        page_texts = extract_text_from_tiff_pages(tiff_bytes)
        return page_texts, "TIFF"

    else:
        return [f"Unsupported file format: {file_extension}"], "Unknown"


def get_pdf_pages(uploaded_file):
    """Extract PDF pages for reordering."""
    uploaded_file.seek(0)
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    return pdf_reader


def reorder_pdf_by_category(uploaded_file, page_categories):
    """Reorder PDF pages by category and return the reordered PDF bytes."""
    try:
        uploaded_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        
        # Create a list of (page_index, category) tuples
        page_category_pairs = [(i, page_categories[i]) for i in range(len(page_categories))]
        
        # Group pages by category
        category_groups = {}
        for page_idx, category in page_category_pairs:
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(page_idx)
        
        # Sort categories (you can customize the order here)
        # Using the order from FILE_TYPE_EXTENSIONS as a base, then alphabetical for others
        category_order = list(FILE_TYPE_EXTENSIONS.keys())
        other_categories = [cat for cat in category_groups.keys() if cat not in category_order]
        sorted_categories = [cat for cat in category_order if cat in category_groups] + sorted(other_categories)
        
        # Create new PDF with reordered pages
        pdf_writer = PyPDF2.PdfWriter()
        
        for category in sorted_categories:
            for page_idx in category_groups[category]:
                pdf_writer.add_page(pdf_reader.pages[page_idx])
        
        # Write to bytes
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    except Exception as e:
        raise Exception(f"Error reordering PDF: {str(e)}")


def reorder_tiff_by_category(uploaded_file, page_categories):
    """Reorder TIFF pages by category by converting to PDF first."""
    try:
        uploaded_file.seek(0)
        tiff_bytes = uploaded_file.read()
        
        # Convert TIFF to PDF first
        pdf_bytes = convert_tiff_to_pdf(tiff_bytes)
        
        # Now reorder the PDF
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Create a list of (page_index, category) tuples
        page_category_pairs = [(i, page_categories[i]) for i in range(len(page_categories))]
        
        # Group pages by category
        category_groups = {}
        for page_idx, category in page_category_pairs:
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(page_idx)
        
        # Sort categories
        category_order = list(FILE_TYPE_EXTENSIONS.keys())
        other_categories = [cat for cat in category_groups.keys() if cat not in category_order]
        sorted_categories = [cat for cat in category_order if cat in category_groups] + sorted(other_categories)
        
        # Create new PDF with reordered pages
        pdf_writer = PyPDF2.PdfWriter()
        
        for category in sorted_categories:
            for page_idx in category_groups[category]:
                pdf_writer.add_page(pdf_reader.pages[page_idx])
        
        # Write to bytes
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    except Exception as e:
        raise Exception(f"Error reordering TIFF: {str(e)}")


def get_reordered_page_categories(page_categories):
    """Get the new page categories after reordering."""
    # Create a list of (page_index, category) tuples
    page_category_pairs = [(i, page_categories[i]) for i in range(len(page_categories))]
    
    # Group pages by category
    category_groups = {}
    for page_idx, category in page_category_pairs:
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(page_idx)
    
    # Sort categories
    category_order = list(FILE_TYPE_EXTENSIONS.keys())
    other_categories = [cat for cat in category_groups.keys() if cat not in category_order]
    sorted_categories = [cat for cat in category_order if cat in category_groups] + sorted(other_categories)
    
    # Create new ordered list
    reordered_categories = []
    for category in sorted_categories:
        for _ in category_groups[category]:
            reordered_categories.append(category)
    
    return reordered_categories


def format_reordered_results(reordered_categories):
    """Format the reordered results for display."""
    if not reordered_categories:
        return []
    
    grouped_results = []
    current_category = reordered_categories[0]
    start_page = 1
    end_page = 1
    
    for i in range(1, len(reordered_categories)):
        if reordered_categories[i] == current_category:
            end_page = i + 1
        else:
            # Add the current group
            if start_page == end_page:
                grouped_results.append(f"Page {start_page}: {current_category}")
            else:
                grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
            
            # Start new group
            current_category = reordered_categories[i]
            start_page = i + 1
            end_page = i + 1
    
    # Add the last group
    if start_page == end_page:
        grouped_results.append(f"Page {start_page}: {current_category}")
    else:
        grouped_results.append(f"Pages {start_page}-{end_page}: {current_category}")
    
    return grouped_results


def main():
    st.set_page_config(
        page_title="Document Categorization App",
        page_icon="📄",
        layout="centered"
    )

    st.title("📄 Multi-Page Document Categorization")
    st.subheader("Automatically categorize each page of your PDF and TIFF documents")

    # API Provider Selection
    st.sidebar.header("🔧 Configuration")
    
    # Check which APIs are available    
    openai_available = openai_client is not None
    gemini_available = gemini_client is not None
    
    if not openai_available and not gemini_available:
        st.error("❌ No API keys found! Please set either OPENAI_API_KEY or GEMINI_API_KEY in your environment variables.")
        st.stop()
    
    # API Provider Selection
    available_providers = []
    if openai_available:
        available_providers.append("OpenAI")
    if gemini_available:
        available_providers.append("Gemini")
    
    if len(available_providers) == 1:
        api_provider = available_providers[0].lower()
        st.sidebar.info(f"Using {available_providers[0]} API")
    else:
        api_provider = st.sidebar.selectbox(
            "Choose API Provider:",
            available_providers,
            help="Select which AI model to use for document categorization"
        ).lower()
    
    # Display API status
    st.sidebar.markdown("**API Status:**")
    if openai_available:
        st.sidebar.success("✅ OpenAI API Available")
    else:
        st.sidebar.error("❌ OpenAI API Not Available")
    
    if gemini_available:
        st.sidebar.success("✅ Gemini API Available")
    else:
        st.sidebar.error("❌ Gemini API Not Available")

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

                # Create two columns for original and reordered results
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📋 Original Document Order")
                    st.markdown("**Page-by-Page Classification (Original):**")
                    for result in grouped_results:
                        st.write(f"📄 {result}")
                
                # Get reordered categories and format them
                reordered_categories = get_reordered_page_categories(page_categories)
                reordered_results = format_reordered_results(reordered_categories)
                
                with col2:
                    st.subheader("🔄 Reordered Document Order")
                    st.markdown("**Page-by-Page Classification (After Reordering):**")
                    for result in reordered_results:
                        st.write(f"📄 {result}")
                
                # Generate reordered PDF
                reordered_pdf_bytes = None
                try:
                    uploaded_file.seek(0)
                    file_extension = uploaded_file.name.lower().split('.')[-1]
                    
                    with st.spinner("Generating reordered PDF..."):
                        if file_extension == 'pdf':
                            reordered_pdf_bytes = reorder_pdf_by_category(uploaded_file, page_categories)
                        elif file_extension in ['tiff', 'tif']:
                            reordered_pdf_bytes = reorder_tiff_by_category(uploaded_file, page_categories)
                        
                        if reordered_pdf_bytes:
                            st.success("✅ Reordered PDF generated successfully!")
                            
                            # Download button
                            st.subheader("📥 Download Reordered Document")
                            original_filename = uploaded_file.name
                            file_name_without_ext = original_filename.rsplit('.', 1)[0]
                            download_filename = f"{file_name_without_ext}_reordered.pdf"
                            
                            st.download_button(
                                label="⬇️ Download Reordered PDF",
                                data=reordered_pdf_bytes,
                                file_name=download_filename,
                                mime="application/pdf",
                                help="Download the PDF with pages reordered by category"
                            )
                except Exception as e:
                    st.error(f"❌ Error generating reordered PDF: {str(e)}")
                    st.info("💡 Tip: The categorization is still available, but PDF reordering failed. This may occur with certain PDF formats.")
                
                # Add debug information if requested
                with st.expander("🔍 Debug Information (Confidence Scores)"):
                    st.write("**Individual Page Analysis (Original Order):**")
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
