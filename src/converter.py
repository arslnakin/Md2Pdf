from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, QEventLoop, QTimer, QMarginsF, QSizeF
from PyQt6.QtGui import QPageSize, QPageLayout
import markdown
import os
import pymdownx.superfences
import pymdownx.arithmatex

class Md2PdfConverter:
    def __init__(self):
        # We will use robust CSS from a CDN or embedded, leveraging WebEngine's full browser capabilities
        # Mermaid and MathJax will be loaded from CDN
        self.html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 14px;
                    line-height: 1.6;
                    color: #333;
                    max-width: 100%;
                    margin: 0;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                }}
                h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
                h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }}
                code {{
                    padding: .2em .4em;
                    margin: 0;
                    font-size: 85%;
                    background-color: rgba(27,31,35,.05);
                    border-radius: 3px;
                    font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;
                }}
                pre {{
                    padding: 16px;
                    overflow: auto;
                    font-size: 85%;
                    line-height: 1.45;
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;
                }}
                pre code {{
                    display: inline;
                    padding: 0;
                    margin: 0;
                    overflow: visible;
                    line-height: inherit;
                    word-wrap: normal;
                    background-color: transparent;
                    border: 0;
                }}
                blockquote {{
                    padding: 0 1em;
                    color: #6a737d;
                    border-left: 0.25em solid #dfe2e5;
                    margin: 0;
                }}
                table {{
                    border-spacing: 0;
                    border-collapse: collapse;
                    margin-top: 0;
                    margin-bottom: 16px;
                    width: 100%;
                }}
                table th, table td {{
                    padding: 6px 13px;
                    border: 1px solid #dfe2e5;
                }}
                table th {{
                    font-weight: 600;
                    background-color: #f6f8fa;
                }}
                img {{ max-width: 100%; box-sizing: content-box; background-color: #fff; }}
                
                /* Mermaid Centering */
                .mermaid {{
                    display: flex;
                    justify-content: center;
                    margin: 20px 0;
                }}
            </style>
            
            <!-- MathJax Configuration -->
            <script>
            window.MathJax = {{
                tex: {{
                    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                    processEscapes: true
                }},
                options: {{
                    ignoreHtmlClass: 'tex2jax_ignore',
                    processHtmlClass: 'tex2jax_process'
                }}
            }};
            </script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
            
            <!-- Mermaid JS (Version 10.9.1) -->
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
        </head>
        <body>
            {content}
            
            <script>
                // 1. Transform superfences output for Mermaid
                document.querySelectorAll('pre code.language-mermaid').forEach(el => {{
                    let pre = el.parentElement;
                    let div = document.createElement('div');
                    div.className = 'mermaid';
                    div.textContent = el.textContent;
                    pre.replaceWith(div);
                }});

                // 2. Run Mermaid
                if (window.mermaid) {{
                    mermaid.initialize({{ startOnLoad: false, theme: 'default' }});
                    mermaid.run({{
                        querySelector: '.mermaid'
                    }});
                }}
            </script>
        </body>
        </html>
        """

    def convert(self, input_path, output_path=None):
        if not output_path:
            output_path = os.path.splitext(input_path)[0] + ".pdf"

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Convert MD to HTML with extensions for Math and Code
            html_body = markdown.markdown(
                md_content, 
                extensions=[
                    'extra', 
                    'codehilite', 
                    'tables', 
                    'toc',
                    'pymdownx.arithmatex',
                    'pymdownx.superfences',
                    'pymdownx.highlight',
                    'pymdownx.inlinehilite',
                    'pymdownx.magiclink',
                    'pymdownx.tasklist'
                ],
                extension_configs={
                    'pymdownx.arithmatex': {
                        'generic': True
                    },
                    'pymdownx.superfences': {
                         "disable_indented_code_blocks": True
                    }
                }
            )
            
            full_html = self.html_template.format(content=html_body)
            
            # --- WebEngine Async PDF Generation Loop ---
            page = QWebEnginePage()
            
            # CRITICAL: Allow local content to access remote CDN scripts (Mermaid/MathJax)
            settings = page.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            
            # Use EventLoop to wait for signals
            loop = QEventLoop()
            
            # 1. Load HTML
            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(input_path)) + os.sep)
            page.setHtml(full_html, base_url)
            
            # Wait for load finished (initial DOM ready)
            page.loadFinished.connect(lambda ok: loop.quit())
            loop.exec()
            
            # 2. Short delay for JS rendering (Mermaid/MathJax async processing)
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(3000) # Wait 3 seconds
            loop.exec()
            
            # 3. Print to PDF
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(15, 15, 15, 15),
                QPageLayout.Unit.Millimeter
            )
            
            page.printToPdf(output_path, layout)
            
            # Wait for PDF writing to finish
            page.pdfPrintingFinished.connect(lambda result: loop.quit())
            loop.exec()
            
            # Cleanup
            page.deleteLater()
            
            return True
            
        except Exception as e:
            print(f"PDF Dönüştürme Hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
