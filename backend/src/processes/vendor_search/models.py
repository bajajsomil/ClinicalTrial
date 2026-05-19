from typing import List, Any, Dict, Union, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, DirectoryPath, constr, validator

class VendorSearch(BaseModel):
    vendor_name : str
    vendor_category : str
    tavily_api_key: Optional[str] = None

class TavilyResponseModel(BaseModel):
    search_result : List
    answer : str
    latency_seconds : Optional[float] = None

class VendorInfo(BaseModel):
    vendor_name: str
    vendor_category: str
    start_year: int
    end_year: int

class AnalysisResult(BaseModel):
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    positive_news: Dict[str, Any] = Field(default_factory=dict)
    negative_news: Dict[str, Any] = Field(default_factory=dict)
    token_usage_per_model: Optional[Dict[str, Dict[str, int]]] = None

class VendorFactItem(BaseModel):
    type: str
    title: str
    summary: str
    date: Optional[str] = None
    facts: List[str] = []
    source_url: Optional[str] = None


class VendorSection(BaseModel):
    vendor_name: str
    vendor_category: str
    question_category: str
    vendor_capabilities: Optional[List[VendorFactItem]] = None
    vendor_positive_news: Optional[List[VendorFactItem]] = None
    vendor_negative_news: Optional[List[VendorFactItem]] = None


class VendorSearchOutput(BaseModel):
    capabilities: VendorSection
    positive_news: VendorSection
    negative_news: VendorSection

class VendorSearchResponse(BaseModel):
    success: bool
    output: Optional[VendorSearchOutput] = None
    error: Optional[str] = None
