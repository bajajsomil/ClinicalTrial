## src/models.py
from typing import List, Any, Dict, Union, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, DirectoryPath, constr, validator

class DecodeJsonResult(BaseModel):
    data: Any = None
    error: Union[str, None] = None

class AzureResponseModel(BaseModel):
    content: Union[str, dict]
    input_tokens: int
    output_tokens: int
    model: str
    latency_seconds: Optional[float] = None
    logprobs:Optional[float]=None

class PageExtractionResult(BaseModel):
    page_number: int
    content: str


class DocumentExtractionResult(BaseModel):
    pages: List[PageExtractionResult]

class PDFTextPages(BaseModel):
    pages: List[str]

class IndexPages(BaseModel):
    start_page: int
    end_page: int

class SectionExtraction(BaseModel):
    sections: Dict[str, Any]

class WorkPackageSummary(BaseModel):
    """Pydantic model representing the full summary of a Work Package."""
    finance_markdown: str
    performance_markdown: str
    program_summary_markdown: str


class VendorFinanceInfo(BaseModel):
    """
    Pydantic model representing key finance information of a work package.
    """
    vendor_name: str
    work_package_type: str
    contract_value: float
    discount_value: float
