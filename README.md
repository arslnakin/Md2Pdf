# Md2Pdf Converter

An advanced, modern desktop application built with Python and PyQt6 that converts Markdown (.md) documents into high-quality PDF files. It features support for **LaTeX mathematics** and **Mermaid diagrams**, making it perfect for technical documentation.

## Features

*   **Modern UI**: Sleek dark theme interface built with PyQt6.
*   **Rich Content Support**:
    *   **LaTeX**: Renders mathematical formulas using MathJax (e.g., `$$ E=mc^2 $$`).
    *   **Mermaid.js**: Automatically renders flowcharts, sequence diagrams, and gantt charts.
    *   **Code Highlighting**: Syntax highlighting for code blocks.
    *   **Tables & Images**: Full support for standard Markdown tables and images.
*   **Batch Processing**: Convert multiple files at once.
*   **Drag & Drop**: Easily add files by dragging them into the application window.
*   **PDF Engine**: Uses the powerful Chromium-based `QWebEngine` for pixel-perfect rendering.

## Installation

1.  Ensure you have Python 3.8+ installed.
2.  Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python src/main.py
```

1.  **Add Files**: Drag and drop your `.md` files or use the generic "Add File" button.
2.  **Select Output (Optional)**: Choose a specific folder for PDFs, or leave default (same folder as source).
3.  **Convert**: Click "Convert to PDF" and wait for the process to complete.

## Architecture & Workflow

Understanding how the code works is straightforward. Below is the full execution flow of the application.

```mermaid
graph TD
    subgraph User Interface [src/main.py]
        Start([Start App]) --> InitUI[Initialize MainWindow]
        InitUI --> LoadCSS[Load styles.qss]
        LoadCSS --> WaitUser{User Action}
        WaitUser -->|Drag & Drop| AddToList[Add Files to List]
        WaitUser -->|Click Convert| StartLoop[Start Conversion Loop]
    end

    subgraph Conversion Logic [src/converter.py]
        StartLoop -->|For each file| ReadMD[Read .md File]
        ReadMD --> ParseMD[Parse Markdown to HTML]
        ParseMD -->|Extensions: Math, Mermaid| InjectHTML[Inject into HTML Template]
        InjectHTML --> LoadWeb[Load into QWebEnginePage]
        LoadWeb -->|LocalContentCanAccessRemoteUrls| RenderJS[Execute MathJax & Mermaid JS]
        RenderJS -->|Wait 3s| PrintPDF[Print to PDF (QPageLayout)]
    end

    subgraph Output
        PrintPDF --> SavePDF[Save .pdf File]
        SavePDF --> UpdateUI[Update Progress Bar]
        UpdateUI --> CheckNext{More Files?}
        CheckNext -->|Yes| ReadMD
        CheckNext -->|No| Finish([Show Success Message])
    end
```

## Code Breakdown

### 1. `src/main.py` (The Frontend)
*   **`MainWindow`**: This is the main class inheriting from `QMainWindow`. It sets up the layout, buttons, and list widget.
*   **`load_stylesheet()`**: Loads the CSS file to give the app its dark theme.
*   **`start_conversion()`**: This method is triggered when you click the convert button. It locks the UI, sets up the progress bar, and loops through the selected files. Inside the loop, calls `processEvents()` to keep the window responsive while calling the converter.

### 2. `src/converter.py` (The Backend)
*   **`Md2PdfConverter`**: The core class responsible for handling the file conversion.
*   **Markdown Parsing**: Uses the `markdown` library with `pymdownx` extensions to convert text into HTML. It enables features like `arithmatex` (Math) and `superfences` (Mermaid blocks).
*   **HTML Template**: Wraps the converted content in a robust HTML structure that includes CDN links for **MathJax** and **Mermaid.js**.
*   **QWebEngine**: This is the secret sauce. Instead of a basic PDF writer, we spin up a headless web browser instance (`QWebEnginePage`).
    *   It loads the HTML.
    *   It waits (via `QTimer` & `QEventLoop`) for the JavaScript (MathJax/Mermaid) to finish rendering the diagrams.
    *   Finally, it uses `printToPdf` to capture the rendered page as a PDF file.

## Requirements

*   `PyQt6`
*   `PyQt6-WebEngine`
*   `Markdown`
*   `Pymdown-extensions`
*   `Pygments`
