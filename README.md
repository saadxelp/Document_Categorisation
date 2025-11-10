# Document Categorization App

This Streamlit application automatically categorizes PDF and TIFF documents (including scanned or image-based PDFs) into one of the following categories:

- Claim Form
- Discharge Summary
- Reports
- Hospital Bills
- Pharmacy Bills
- Diagnostic Bills
- KYC
- Pre-Auth form C
- Cancelled cheque
- Others

## Features

- **Multi-stage categorization**: Uses a combination of header analysis, keyword matching, and AI language models
- **Dual AI Support**: Choose between OpenAI GPT-3.5-turbo or Google Gemini for document classification
- **OCR capability**: Extracts text from scanned or image-based PDFs and TIFF files
- **Multi-page analysis**: Processes each page independently with context-aware continuity
- **Confidence scoring**: Provides confidence levels for classification results
- **File type mapping**: Automatic file extension assignment based on document category

## Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/document-categorization-app.git
   cd document-categorization-app
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR:

   - **Windows**: Download and install from [here](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `apt-get install tesseract-ocr`

4. For PDF to image conversion, you'll need Poppler:
   - **Windows**: Download binaries and add to PATH
   - **macOS**: `brew install poppler`
   - **Linux**: `apt-get install poppler-utils`

## Configuration

1. Create a `.env` file in the project directory with your API keys:

   ```
   # OpenAI API Key (optional)
   OPENAI_API_KEY=your_openai_api_key_here

   # Google Gemini API Key (optional)
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

   **Note**: You need at least one of the above API keys to use the application. The app will automatically detect which APIs are available and allow you to choose between them.

2. Get your API keys:
   - **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Gemini**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## File Type and Extension Mapping

The app automatically assigns file extensions based on document categories:

- **Claim Form** → `C`
- **Discharge Summary** → `D`
- **Reports** → `R`
- **Cancelled cheque** → `Q`
- **Hospital Bills** → `B`
- **Pharmacy Bills** → `P`
- **Diagnostic Bills** → `I`
- **KYC** → `K`
- **Pre-Auth form C** → `PF`

Example: A document categorized as "Claim Form" would be assigned the extension `C`.

## Usage

1. Run the application:

   ```
   streamlit run doc_categorizer_openai.py
   ```

2. Open your web browser and navigate to the URL displayed in the terminal (usually http://localhost:8501).

3. Choose your preferred API provider from the sidebar (OpenAI or Gemini).

4. Upload a PDF or TIFF document using the file uploader.

5. The app will process the document and display:
   - Basic file details
   - Page-by-page analysis with confidence levels
   - Final document categorization with file type mapping
   - Debug information showing individual page analysis
   - Option to view extracted text for each page

## How It Works

The application uses a multi-stage process to categorize documents:

1. **Header Analysis**: Examines the first few lines of the document for explicit mentions of document type
2. **Keyword Matching**: Searches for category-specific keywords throughout the document
3. **AI Classification**: Uses either OpenAI GPT-3.5-turbo or Google Gemini as a fallback for documents that cannot be categorized by simpler methods
4. **Context-Aware Continuity**: For multi-page documents, applies intelligent continuity logic to maintain document type consistency
5. **Confidence Scoring**: Provides confidence levels for each classification decision
6. **File Type Mapping**: Automatically assigns appropriate file extensions based on document categories

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.# Document_Categorization
