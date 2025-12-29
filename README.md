# Bank Statement Parser

A local web application to parse bank statement PDFs and export the transactions to CSV. This tool runs entirely on your machine to ensure privacy.

## Features

- **Drag & Drop UI**: Easy to use interface powered by Streamlit.
- **Local Processing**: No data is sent to external servers.
- **Smart Parsing**:
  - Extracts tables using `pdfplumber`.
  - Automatically identifies Date and Amount columns.
  - Merges separate Debit/Credit columns into a single signed Amount column.
  - extracts Account Number from the statement header.

## Prerequisites

- Python 3.8 or higher
- System dependencies for OCR (Tesseract and Poppler)

### Installing System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr poppler-utils
```

**macOS (Homebrew):**
```bash
brew install tesseract poppler
```

## Installation

1.  Clone this repository or download the source code.
2.  Navigate to the project directory.
3.  Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

To start the web interface, run:

```bash
streamlit run app.py
```

This will open the application in your default web browser (usually at `http://localhost:8501`).

## Usage

1.  Click **Browse files** or drag and drop your bank statement PDF into the upload area.
2.  The application will process the file.
3.  Preview the extracted data in the table.
4.  Click **Download CSV** to save the parsed transactions to your computer.

## Development & Testing

To run the unit tests:

1.  Generate a mock PDF statement:
    ```bash
    python generate_test_pdf.py
    ```
2.  Run the parser test:
    ```bash
    python test_parser.py
    ```
