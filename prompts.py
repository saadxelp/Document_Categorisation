"""
Prompts for document categorization.
This module contains all prompts used for document classification.
"""


def get_document_classification_prompt(processed_text: str) -> str:
    """
    Get the main prompt for document classification.
    
    Args:
        processed_text: The preprocessed text content from the document
        
    Returns:
        The formatted prompt string
    """
    prompt = f"""You are an expert in document classification. 
    Based on the text content below (extracted from a single page of a PDF document, possibly using OCR from scanned or image-based PDFs), 
    identify which category this document page belongs to from the following options:
    
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
    
    CRITICAL CLASSIFICATION RULES (in order of priority):
    1. HEADER-BASED CLASSIFICATION (Highest Priority):
       - If "PRE-APPROVAL CERTIFICATE", "PRE-AUTH", "PRE-AUTHORIZATION", **"REQUEST FOR CASHLESS HOSPITALISATION/HOSPITALIZATION"** in header → "Pre-Auth form C" (HIGHEST PRIORITY AND MUST OVERRIDE ALL OTHER HINTS)
       - If "CLAIM FORM" appears in header/title → "Claim Form"
       - If "CLAIM NO" or "CLAIM NUMBER" appears anywhere in document → "Claim Form" (IMPORTANT: This overrides other classifications UNLESS "REQUEST FOR CASHLESS HOSPITALISATION" is also present)
       - If "DISCHARGE SUMMARY" appears in header/title → "Discharge Summary"  
       - If "CENTRAL KYC REGISTRY", "CERSAI", "KYC APPLICATION FORM", "KNOW YOUR CUSTOMER" in header → "KYC"
       - If "FINAL BILL" or hospital name with billing info in header → "Hospital Bills"
       - If "TEST REPORT", "LAB REPORT", "DIAGNOSTICS" in header → "Reports"
       - If "PHARMACY", "MEDICAL STORE", "CHEMIST" in header → "Pharmacy Bills"
    
    2. CONTENT-BASED CLASSIFICATION:
       - Pre-Auth forms: Estimated expenses, proposed treatment, authorized limit, BEFORE hospitalization language, "TO BE FILLED BY INSURED", future tense (proposed, planned, estimated, expected), "PROPOSED DATE OF HOSPITALIZATION", "ESTIMATED DURATION", "AUTHORIZED LIMIT", "PAC NO", "PRE-APPROVAL CERTIFICATE"
       - Claim Forms: Policy details, patient info, insurance details, TPA ID, claim numbers (CLAIM NO/CLAIM NUMBER), reimbursement fields, past tense (incurred, spent, paid, underwent, hospitalized, treated), "TOTAL AMOUNT CLAIMED", "DATE OF ADMISSION", "DATE OF DISCHARGE" (past dates)
       - Discharge Summaries: Admission/discharge dates, diagnosis, treatment details, clinical summary, follow-up advice, "CONDITION ON DISCHARGE", "TREATMENT GIVEN IN HOSPITAL", "DISCHARGE SUMMARY", "DISCHARGE NOTE", patient name/age/sex with admission details, clinical findings, treatment procedures, medications prescribed, follow-up instructions. CRITICAL: Discharge Summary has CLINICAL information (diagnosis, treatment, procedures) but typically NO itemized billing charges, bill numbers, GST, or pricing details. If you see clinical information (diagnosis, treatment, admission/discharge dates) WITHOUT strong billing indicators (BILL NO, TOTAL BILL AMT, GST, itemized charges), it's likely Discharge Summary.
       - Hospital Bills: Itemized charges for hospital services, room charges, procedure charges, consultation fees, "BILL NO", "TOTAL BILL AMT", "GSTN", "SGST", "CGST", "FINAL BILL", billing statements, invoice details, item codes, rates, amounts, tax information. CRITICAL: Hospital Bills have BILLING/CHARGES information (itemized charges, bill numbers, GST, rates, amounts) and may include patient info but focus is on billing.
       - Pharmacy Bills: Medication names, drug names, tablets, capsules, syrups, prescriptions, dosage info, "PHARMACY", "MEDICAL STORE", "CHEMIST", "DRUGSTORE", medication lists with prices, prescription details. CRITICAL: Pharmacy Bills focus on MEDICATIONS and DRUGS, not hospital services or procedures.
       - Reports: Test results, reference ranges, diagnostic findings, laboratory values, units (mg/dL, mmol/L), NO pricing, "TEST REPORT", "LAB REPORT", "REFERENCE RANGE"
       - KYC: Personal details, identity/address sections, customer info, photograph/signature fields, "CENTRAL KYC REGISTRY", "CERSAI"
       - Cancelled cheque: Bank account numbers, IFSC codes, MICR codes, bank/branch names, "CANCELLED CHEQUE"
    
    3. CONTEXT CLUES (Temporal Indicators):
       - Future tense (proposed, planned, estimated, expected, scheduled, upcoming) + "TO BE FILLED BY INSURED" OR **"REQUEST FOR CASHLESS HOSPITALISATION"** → Pre-Auth form C (HIGHEST PRIORITY)
       - Past tense (incurred, spent, paid, underwent, hospitalized, treated, admitted, discharged) + "CLAIM NO" → Claim Form
       - Presence of "CLAIM NO" or "CLAIM NUMBER" anywhere in document → Claim Form (IMPORTANT: This overrides other classifications UNLESS strong Pre-Auth indicators are present)
       - "PROPOSED DATE OF HOSPITALIZATION" or "ESTIMATED EXPENSES" → Pre-Auth form C
       - "DATE OF ADMISSION" and "DATE OF DISCHARGE" with past dates → Check for billing info: If has "BILL NO", "TOTAL BILL AMT", "GST", itemized charges → Hospital Bills. If has clinical info (diagnosis, treatment, condition on discharge) WITHOUT billing → Discharge Summary. If has "CLAIM NO" → Claim Form.
       - Test values with units but no prices → Reports
       - Service charges with prices → Hospital Bills
       - Medication lists with prices → Pharmacy Bills
       
       CRITICAL DISTINCTION: Discharge Summary vs Hospital Bills vs Pharmacy Bills:
       - Discharge Summary: Clinical information (diagnosis, treatment, procedures, medications prescribed, follow-up) + admission/discharge dates. Typically NO itemized billing, NO bill numbers, NO GST/tax information, NO rates/amounts for services.
       - Hospital Bills: Billing information (itemized charges, bill numbers, GST, rates, amounts, total bill amount) + may include patient info. Focus is on CHARGES and BILLING.
       - Pharmacy Bills: Medication-focused (drug names, tablets, capsules, prescriptions, pharmacy/store name) + prices. Focus is on MEDICATIONS, not hospital services.
    
    4. DOCUMENT BOUNDARY DETECTION:
       - Each page should be classified independently based on its own content
       - Look for clear document headers and content indicators on each individual page
       - If a page has "CLAIM FORM" in the header, it should be classified as "Claim Form"
       - If a page has "DISCHARGE SUMMARY" in the header, it should be classified as "Discharge Summary"
       - If a page has "FINAL BILL" or billing information with itemized charges, it should be classified as "Hospital Bills"
       - However, if a page lacks clear headers but contains content consistent with the previous page's document type (e.g., continuation of a form or summary), consider it part of the same document
    
    IMPORTANT DISTINCTION BETWEEN PRE-AUTH FORM C AND CLAIM FORM:
    - Pre-Auth Form C: Used BEFORE hospitalization/treatment. Contains future-oriented language (proposed, estimated, expected), "REQUEST FOR CASHLESS HOSPITALISATION", "TO BE FILLED BY INSURED", "PROPOSED DATE OF HOSPITALIZATION", "ESTIMATED EXPENSES", "AUTHORIZED LIMIT"
    - Claim Form: Used AFTER hospitalization/treatment. Contains past-oriented language (incurred, spent, paid, underwent), "CLAIM NO", "CLAIM NUMBER", "TOTAL AMOUNT CLAIMED", actual dates of admission/discharge
    
    IMPORTANT: Focus on the MOST PROMINENT document type indicators on THIS SPECIFIC PAGE. If multiple types are present, prioritize based on header information first, then content density. Each page is a separate document that should be classified independently.
    
    Respond with ONLY the category name.
    
    Document content:
    {processed_text[:4000]}
    """
    return prompt


def get_openai_system_message() -> str:
    """
    Get the system message for OpenAI API.
    
    Returns:
        The system message string
    """
    return "You are a document classification expert. Analyze the text and classify it into exactly one category: 'Claim Form', 'Discharge Summary', 'Reports', 'Cancelled cheque', 'Hospital Bills', 'Pharmacy Bills', 'Diagnostic Bills', 'KYC', 'Pre-Auth form C', or 'Others'. Prioritize header-based classification over content analysis. Respond with only the category name."
