import os
import fitz  # PyMuPDF
import tempfile
import html
import tabulate
import pandas as pd
import asyncio
from ftfy import fix_text
from typing import List, Tuple, Dict, Any, Set
from PyPDF2 import PdfWriter, PdfReader
from azure.core.exceptions import AzureError
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient, AnalyzeResult, DocumentTable
from azure.identity import DefaultAzureCredential
from config.config import Config
from src.adapters.logger import log_with_span
from src.models import DocumentExtractionResult, PageExtractionResult


class DocumentIntelligence:
    """
    Handles text extraction using PyMuPDF + Azure Document Intelligence.
    Routes generic text pages to PyMuPDF and complex pages (Images/Tables) to Azure.
    """

    def __init__(self) -> None:
        try:
            self.api_key: str = Config.AZURE_DOCUMENT_INTELLIGENCE_KEY
            self.endpoint: str = Config.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT

            if not self.endpoint:
                raise ValueError("Azure Document Intelligence endpoint is missing.")

            if self.api_key:
                credential = AzureKeyCredential(self.api_key)
            else:
                credential = DefaultAzureCredential()

            self.client: DocumentAnalysisClient = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=credential,
                headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"},
            )

            log_with_span(
                "Document Intelligence client initialized",
                "Document-Intelligence.Init",
                "info",
                log_extra={
                    "service_name": "Document Intelligence",
                    "output": "client-initialized",
                    "status": "Success"
                }
            )

        except Exception as e:
            log_with_span(
                "Failed to initialize Document Intelligence client",
                "Document-Intelligence.Init",
                "error",
                log_extra={
                    "service_name": "Document Intelligence",
                    "status": "Failed",
                    "error": str(e)
                }
            )
            raise


    async def detect_page_types(self, pdf_path: str) -> Tuple[List[int], List[int]]:
        """
        Async version using concurrency for page processing.
        """
        text_pages = []
        azure_pages = []

        try:
            doc = fitz.open(pdf_path)

            async def process_page(i, page):
                try:
                    text = await asyncio.to_thread(page.get_text, "text")
                    has_text = bool(text.strip())

                    if not has_text:
                        return ("azure", i)

                    try:
                        tables = await asyncio.to_thread(page.find_tables)
                        has_tables = bool(tables.tables)
                    except Exception:
                        has_tables = False

                    if has_tables:
                        return ("azure", i)
                    else:
                        return ("text", i)

                except Exception as e:
                    log_with_span(
                        f"Error detecting content on page {i + 1}",
                        "Document-Intelligence.PageDetection",
                        "warning",
                        log_extra={"error": str(e)}
                    )
                    return ("azure", i)

            # 🔥 Run all pages concurrently
            tasks = [
                process_page(i, page)
                for i, page in enumerate(doc)
            ]

            results = await asyncio.gather(*tasks)

            # Collect results
            for page_type, i in results:
                if page_type == "text":
                    text_pages.append(i)
                else:
                    azure_pages.append(i)

            log_with_span(
                "Page type detection complete",
                "Document-Intelligence.PageDetection",
                "info",
                log_extra={
                    "input": pdf_path,
                    "output": {
                        "text_pages_count": len(text_pages),
                        "azure_pages_count": len(azure_pages)
                    },
                    "status": "Success"
                }
            )

            print("TEXT", text_pages)
            print("AZURE", azure_pages)

            return text_pages, azure_pages


        except Exception as e:
            log_with_span(
                "Failed to detect page types",
                "Document-Intelligence.PageDetection",
                "error",
                log_extra={"error": str(e)}
            )
            raise


    # --------------------------------------------------------------------------------
    def clean_text_auto(self, text: str) -> str:
        text = fix_text(text, normalization="NFC")
        text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())
        return text

    # --------------------------------------------------------------------------------
    def table_to_html(self, table: DocumentTable) -> str:
        """
        Converts an Azure Form Recognizer table object to an HTML table string, 
        then tries to convert it to a Markdown table using tabulate.
        """
        table_html: str = "<table>"
        rows: List[List[Any]] = [
            sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index)
            for i in range(table.row_count)
        ]

        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = "th" if (cell.kind in ["columnHeader", "rowHeader"]) else "td"
                cell_spans = ""
                if cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html += "</tr>"
        table_html += "</table>"

        try:
            df: pd.DataFrame = pd.read_html(table_html)[0]
            df.replace("", float("NaN"), inplace=True)
            df.dropna(how="all", axis=1, inplace=True)
            df.replace(float("NaN"), "", inplace=True)
            table_str: str = tabulate.tabulate(df.to_records(index=False), headers=df.columns, tablefmt="github")
            return "\n\n" + table_str + "\n\n"
        except Exception:
            # Fallback if tabulate/pandas fails
            return "\n\n" + table_html + "\n\n"
        

    # --------------------------------------------------------------------------------
    def process_azure_page_result(self, result: AnalyzeResult, page_index: int) -> str:
        """
        Reconstructs a SINGLE page's text from Azure result, inserting tables in-place 
        using character offsets.
        """
        page = result.pages[page_index]
        
        # Filter tables that belong to this specific page
        tables_on_page: List[DocumentTable] = [
            table for table in result.tables
            if table.bounding_regions and table.bounding_regions[0].page_number == page.page_number
        ]

        # Azure spans map to the full 'content' string of the result
        page_offset: int = page.spans[0].offset
        page_length: int = page.spans[0].length

        # Create a map of character index -> table_id (or -1 if text)
        table_chars: List[int] = [-1] * page_length

        for table_id, table in enumerate(tables_on_page):
            for span in table.spans:
                # Map table span relative to the page start
                for i in range(span.length):
                    idx = span.offset - page_offset + i
                    if 0 <= idx < page_length:
                        table_chars[idx] = table_id

        page_text: str = ""
        added_tables: Set[int] = set()

        # Reconstruct text character by character
        for idx, table_id in enumerate(table_chars):
            if table_id == -1:
                # It's normal text
                page_text += result.content[page_offset + idx]
            elif table_id not in added_tables:
                # It's the start of a table we haven't added yet
                page_text += self.table_to_html(tables_on_page[table_id])
                added_tables.add(table_id)
            # If table_id is in added_tables, we skip the character (it's part of the table text we already replaced)

        # Cleanup artifacts
        cleaned_text = page_text.replace(":selected:", "").replace(":unselected:", "")
        return self.clean_text_auto(cleaned_text)


    def extract_text_pages_via_azure_read(self, pdf_path: str, page_indices: List[int]) -> Dict[int, str]:
        """
        Extracts normal text pages using Azure prebuilt-read model.
        """
        if not page_indices:
            return {}

        results_by_page: Dict[int, str] = {}
        tmp_path = None

        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for i in page_indices:
                writer.add_page(reader.pages[i])

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                with open(tmp_path, "wb") as f:
                    writer.write(f)

            with open(tmp_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    "prebuilt-read",   # 👈 READ MODEL
                    document=f
                )

            result = poller.result()

            for idx, page in enumerate(result.pages):
                original_page_index = page_indices[idx]

                page_offset = page.spans[0].offset
                page_length = page.spans[0].length

                page_text = result.content[page_offset: page_offset + page_length]
                cleaned = self.clean_text_auto(page_text)

                formatted = f"Page ## Pick this Page Number ## {original_page_index + 1}\n{cleaned}\n"
                results_by_page[original_page_index] = formatted

        except Exception as e:
            log_with_span("Read model extraction failed", "Document-Intelligence.Read", "error", log_extra={"error": str(e)})

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        return results_by_page

    
    
    # --------------------------------------------------------------------------------
    def extract_complex_pages_via_azure(self, pdf_path: str, page_indices: List[int], azure_model = "prebuilt-layout") -> Dict[int, str]:
        """
        Extracts content from images or table-heavy pages using Azure Document Intelligence.
        Uses character offsets to replace table text with Markdown tables in-place.
        """
        if not page_indices:
            return {}

        results_by_page: Dict[int, str] = {}
        tmp_path = None

        try:
            # Create a temporary PDF containing only the required pages
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for i in page_indices:
                writer.add_page(reader.pages[i])

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
                with open(tmp_path, "wb") as f:
                    writer.write(f)

            log_with_span(
                "Running Azure Layout Model on complex pages",
                "Document-Intelligence.Azure",
                "info",
                log_extra={"page_count": len(page_indices), "status": "Started"}
            )

            with open(tmp_path, "rb") as f:
                # Using prebuilt-layout (or prebuilt-document) is required for table structure
                poller = self.client.begin_analyze_document(azure_model, document=f)
            
            result = poller.result()

            # Iterate through the pages returned by Azure
            # Note: Azure returns pages indexed 0, 1, 2... relative to the TEMP PDF
            for idx, _ in enumerate(result.pages):
                # Retrieve the original PDF page number
                original_page_index = page_indices[idx]
                
                # Process the page using the offset logic
                processed_content = self.process_azure_page_result(result, idx)
                
                formatted_final = f"Page ## Pick this Page Number ## {original_page_index + 1}\n{processed_content}\n"
                results_by_page[original_page_index] = formatted_final

            log_with_span(
                "Azure extraction completed",
                "Document-Intelligence.Azure",
                "info",
                log_extra={"status": "Success"}
            )

        except AzureError as ae:
            log_with_span("Azure Analysis failed", "Document-Intelligence.Azure", "error", log_extra={"error": str(ae)})
        except Exception as e:
            log_with_span("Unexpected Azure processing error", "Document-Intelligence.Azure", "error", log_extra={"error": str(e)})
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

        return results_by_page

    # --------------------------------------------------------------------------------
    async def extract_text_from_pdf_combined(
        self,
        pdf_path: str,
        mode: str = "hybrid",  # options: hybrid | azure_read_all | azure_layout_all
        azure_model: str = "prebuilt-layout"
    ) -> DocumentExtractionResult:
        """
        Combined extraction with configurable strategy.

        mode:
            - hybrid: detect pages → text via READ, complex via LAYOUT
            - azure_read_all: all pages via Azure READ
            - azure_layout_all: all pages via Azure LAYOUT (or DOCUMENT)

        azure_model:
            - used only when mode = azure_layout_all
            - options: prebuilt-layout | prebuilt-document
        """

        try:
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                all_page_indices = list(range(total_pages))

            # -------------------------------
            # MODE 1: HYBRID (DEFAULT)
            # -------------------------------
            if mode == "hybrid":
                text_pages, complex_pages = await self.detect_page_types(pdf_path)

                # Run both in parallel
                text_task = asyncio.to_thread(
                    self.extract_text_pages_via_azure_read,
                    pdf_path,
                    text_pages
                )

                azure_task = asyncio.to_thread(
                    self.extract_complex_pages_via_azure,
                    pdf_path,
                    complex_pages,
                    azure_model
                )

                text_results, azure_results = await asyncio.gather(
                    text_task,
                    azure_task
                )
            # -------------------------------
            # MODE 2: AZURE READ FOR ALL
            # -------------------------------
            elif mode == "azure_read_all":
                text_results = self.extract_text_pages_via_azure_read(pdf_path, all_page_indices)
                azure_results = {}

            # -------------------------------
            # MODE 3: AZURE LAYOUT/DOCUMENT FOR ALL
            # -------------------------------
            elif mode == "azure_layout_all":
                text_results = {}
                azure_results = self.extract_complex_pages_via_azure(
                    pdf_path,
                    all_page_indices,
                    azure_model
                )

            else:
                raise ValueError(f"Invalid mode: {mode}")

            # -------------------------------
            # Combine Results
            # -------------------------------
            all_pages: List[PageExtractionResult] = []

            for i in range(total_pages):
                content = text_results.get(i) or azure_results.get(i) or ""
                all_pages.append(PageExtractionResult(page_number=i + 1, content=content))

            log_with_span(
                "PDF extraction complete",
                "Document-Intelligence.Extraction",
                "info",
                log_extra={
                    "input": pdf_path,
                    "mode": mode,
                    "total_pages": total_pages,
                    "status": "Success"
                }
            )

            return DocumentExtractionResult(pages=all_pages)

        except Exception as e:
            log_with_span(
                "Failed to extract PDF",
                "Document-Intelligence.Extraction",
                "error",
                log_extra={"error": str(e)}
            )
            raise


# Singleton instance
document_intelligence = DocumentIntelligence()