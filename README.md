# Document Categorization App

This Streamlit application automatically categorizes PDF documents (including scanned or image-based PDFs) into one of the following categories:
- Claim Form
- Discharge Summary
- Report
- Hospital Bill
- Others

## Features

- **Multi-stage categorization**: Uses a combination of header analysis, keyword matching, and OpenAI's language models
- **OCR capability**: Extracts text from scanned or image-based PDFs
- **Filename validation**: Validates if the document content matches the expected type based on filename pattern
- **Multi-page analysis**: Examines up to 3 pages to ensure accurate categorization
- **Confidence scoring**: Provides confidence levels for classification results

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

1. Create a `.env` file in the project directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Filename Pattern Convention

The app recognizes specific patterns in filenames to validate document types:
- `_C` in filename indicates Claim Form
- `_R` in filename indicates Report
- `_B` in filename indicates Hospital Bill
- `_D` in filename indicates Discharge Summary

Example: `patient123_C.pdf` would be expected to be a Claim Form.

## Usage

1. Run the application:
   ```
   streamlit run app.py
   ```

2. Open your web browser and navigate to the URL displayed in the terminal (usually http://localhost:8501).

3. Upload a PDF document using the file uploader.

4. The app will process the document and display:
   - Basic file details
   - Page-by-page analysis with confidence levels
   - Final document categorization
   - Validation result if a filename pattern was detected
   - Option to view extracted text

## How It Works

The application uses a multi-stage process to categorize documents:

1. **Header Analysis**: Examines the first few lines of the document for explicit mentions of document type
2. **Keyword Matching**: Searches for category-specific keywords throughout the document
3. **Footer Analysis**: Checks the last few lines for indicators of document type (especially for reports)
4. **OpenAI API**: Uses GPT-3.5-turbo as a fallback for documents that cannot be categorized by simpler methods
5. **Validation**: Compares the detected category with the expected category based on filename pattern

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.# Document_Categorization
