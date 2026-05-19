from typing import List, Any, Dict, Union, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, DirectoryPath, constr, validator

class ProcessSectionResponse(BaseModel):
    nested_result: Dict[str, Any]
    input_tokens: int = Field(..., description="Number of input tokens used")
    output_tokens: int = Field(..., description="Number of output tokens used")
    model: str

class SectionImpact(BaseModel):
    added: Dict[str, Any]
    removed: Dict[str, Any]

class ComparisonResult(BaseModel):
    differences: Dict[str, Any]  # <-- was List
    section_added_or_removed_impact: Dict[str, Any]  # <-- was List
    model_tokens: Dict[str, Dict[str, int]]
    

class ComparisonResponseData(BaseModel):
    differences: Dict[str, Any]
    section_added_or_removed_impact: SectionImpact
    summary: str

class ComparisonAPIResponse(BaseModel):
    success: bool
    result: ComparisonResponseData
    error: Any = None