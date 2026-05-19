import re
import os
import json
import time
import inspect
import tiktoken
from functools import wraps
from collections import defaultdict
from pydantic import BaseModel
from src.adapters.logger import log_with_span
from typing import  Any, Callable, Coroutine, TypeVar, Union, Dict, Optional, List
from src.processes.protocol_analyzer.models import ExtractedField, FieldResult, ChunkResult2, ChunkResult3, ChunkResult, ChunkResult4

F = TypeVar("F", bound=Callable[..., Any])

def timing_decorator(func: F) -> F:
    """
    Decorator to measure and log the execution time of a function or coroutine.

    For synchronous functions, it returns a tuple of (result, duration_seconds).
    For asynchronous functions (coroutines), it awaits the function and returns the same tuple.

    Parameters:
        func (Callable): The function or coroutine to wrap.

    Returns:
        Callable: A wrapped function or coroutine that returns (result, duration_seconds)
                  and logs the execution time.
    """
    if inspect.iscoroutinefunction(func):  # async case
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Union[tuple[Any, float], Coroutine[Any, Any, tuple[Any, float]]]:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result, time.time() - start_time
            finally:
                duration = time.time() - start_time
                log_with_span(f"{func.__name__} took {duration:.4f} seconds", "Timing Decorator","info",log_extra={'Function Name': func.__name__, 'Duration': duration, 'Async FUnction': True, 'status': 'Completed'})
        return wrapper  # type: ignore
    else:  # sync case
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result, time.time() - start_time
            finally:
                duration = time.time() - start_time
                log_with_span(f"{func.__name__} took {duration:.4f} seconds", "Timing Decorator","info",log_extra={'Function Name': func.__name__, 'Duration': duration, 'Async FUnction': False, 'status': 'Completed'})
        return wrapper  # type: ignore


def nested_set(dic: Dict[str, Any], keys: List[str], value: Any):
    """
    Set a value in a nested dictionary given a list of keys.
    """
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

def clean_json(data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """Recursively clean JSON data by removing flagged items, empty fields, and empty dicts.

    Rules:
        - If a dict contains `"flag": True`, remove that dict entirely.
        - If a dict contains `"flag": False` but all other values are empty,
          remove that dict as well.
        - Always remove the `"flag"` key if present.
        - Remove any key if its value is empty (None, "", {}, []).
        - Recursively process nested dicts and lists.
        - Remove keys if their nested dict becomes empty after cleaning.

    Args:
        data (Union[Dict[str, Any], List[Any]]): Input JSON-like structure.

    Returns:
        Union[Dict[str, Any], List[Any]]: Cleaned JSON structure.
    """
    if isinstance(data, dict):
        keys_to_delete: List[str] = []
        for k, v in list(data.items()):
            if isinstance(v, dict):
                # Case 1: Remove flagged True dicts
                if v.get("flag") is True:
                    keys_to_delete.append(k)
                    continue

                # Track flag value and remove the key
                flag_value = v.pop("flag", None)

                # Recursively clean nested dict
                clean_json(v)

                # Case 2: If flag was False and all values empty -> remove dict
                if flag_value is False and all(
                    not val for val in v.values()
                ):
                    keys_to_delete.append(k)
                    continue

                # Case 3: Remove if empty
                if not v:
                    keys_to_delete.append(k)

            elif isinstance(v, list):
                # Clean list items
                cleaned_list = []
                for item in v:
                    cleaned_item = clean_json(item)
                    if cleaned_item not in (None, "", {}, []):
                        cleaned_list.append(cleaned_item)
                data[k] = cleaned_list

                # If list ends up empty, drop key
                if not data[k]:
                    keys_to_delete.append(k)

            else:
                # Case 4: Remove key if value is empty
                if v in (None, "", [], {}):
                    keys_to_delete.append(k)

        # Delete keys collected
        for k in keys_to_delete:
            data.pop(k)

    elif isinstance(data, list):
        # Process list elements
        cleaned_list = []
        for item in data:
            cleaned_item = clean_json(item)
            if cleaned_item not in (None, "", {}, []):
                cleaned_list.append(cleaned_item)
        return cleaned_list

    return data

def remove_numbers_from_section(
    d: Union[Dict[str, Any], Any]
) -> Union[Dict[str, Any], Any]:
    """Remove section/roman numbers from dictionary keys recursively."""

    # Matches: "1", "1.", "1.1.", "1.1.1", "2)", "II.", "iv)", "1. Objectives", etc.
    pattern = r'^\s*(?:\d+(?:\.\d+)*[\.\)]?|\b[IVXLCDMivxlcdm]+[\.\)])\s*'

    if isinstance(d, dict):
        new_dict: Dict[str, Any] = {}
        for k, v in d.items():
            new_key = re.sub(pattern, '', k).strip()
            new_dict[new_key] = remove_numbers_from_section(v)
        return new_dict

    elif isinstance(d, list):
        return [remove_numbers_from_section(item) for item in d]

    return d


# ============================================================
# 1️⃣ HEADER DEPTH DETECTION
# ============================================================
def get_header_depth(header: str) -> int:
    """
    Determine hierarchy depth based on numbering segments.
    Examples:
        1.                -> 1
        1.1               -> 2
        1.1.1             -> 3
        3.2.2 Title       -> 3
        I.A.1             -> 3
    """
    match = re.match(r'^([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)', header)
    if match:
        return match.group(1).count('.') + 1
    return 1


# ============================================================
# 2️⃣ NORMALIZE PDF TEXT (CRITICAL FIX)
# ============================================================
import re

def normalize_pdf_text(text: str) -> str:
    """
    Normalize PDF text:
    - Fix hyphen line breaks: time-\naveraged -> time-averaged
    - Remove internal line breaks
    - Normalize ALL hyphen spacing to single space on both sides
      (A-B, A -B, A- B, A - B -> A - B)
    - Collapse multiple spaces
    """

    # 1️⃣ Fix hyphen line breaks
    text = re.sub(r'-\s*\n\s*', '-', text)

    # 2️⃣ Remove internal line breaks
    text = re.sub(r'\s*\n\s*', ' ', text)

    # 3️⃣ Normalize hyphen spacing everywhere
    text = re.sub(r'\s*-\s*', ' - ', text)

    # 4️⃣ Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_header(header: str) -> str:
    """
    Normalize header same way as PDF text.
    Also normalize hyphen spacing variations:
    - A-B
    - A -B
    - A- B
    - A - B
    All become: A - B
    """

    # 1️⃣ Remove hyphen line breaks from PDFs
    header = re.sub(r'-\s*\n\s*', '-', header)

    # 2️⃣ Normalize ALL hyphen spacing to single-space on both sides
    # Convert any spacing around '-' into ' - '
    header = re.sub(r'\s*-\s*', ' - ', header)

    # 3️⃣ Normalize multiple spaces
    header = re.sub(r'\s+', ' ', header)

    return header.strip()
# ============================================================
# 3️⃣ GET ALL HEADERS (FLAT ORDERED LIST)
# ============================================================
def get_all_headers(section_dict: Dict[str, Any]) -> List[str]:
    headers: List[str] = []

    def walk(d: Dict[str, Any]) -> None:
        for k, v in d.items():
            headers.append(k)
            if isinstance(v, dict):
                walk(v)

    walk(section_dict)
    return headers


# ============================================================
# 4️⃣ COMPUTE HIERARCHY-AWARE BOUNDARIES
# ============================================================
def compute_boundaries(headers: List[str]) -> Dict[str, Optional[str]]:
    """
    For each header:
    - If it has children → boundary is first child
    - Else → boundary is next header with depth <= current depth
    """

    boundaries: Dict[str, Optional[str]] = {}

    for i, header in enumerate(headers):
        current_depth = get_header_depth(header)
        boundary = None

        # 1️⃣ FIRST: Check if next header is a child
        if i + 1 < len(headers):
            next_depth = get_header_depth(headers[i + 1])
            if next_depth > current_depth:
                # First child — stop here
                boundary = headers[i + 1]
                boundaries[header] = boundary
                continue

        # 2️⃣ Otherwise behave like before
        for j in range(i + 1, len(headers)):
            next_depth = get_header_depth(headers[j])
            if next_depth <= current_depth:
                boundary = headers[j]
                break

        boundaries[header] = boundary

    return boundaries


def normalize_text(text: str) -> str:
    """
    Normalize full PDF text for consistent matching.
    """

    text = re.sub(r'-\s*\n\s*', '-', text)

    text = re.sub(r'\s*-\s*', ' - ', text)

    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def extract_between(
    normalized_text: str,
    start_header: str,
    end_header: Optional[str]
) -> str:
    """
    Extract content between two headers using index slicing.
    Much more stable than regex lookahead for PDFs.
    """

    start_header_norm = normalize_header(start_header).lower()
    start_idx = normalized_text.lower().find(start_header_norm)

    if start_idx == -1:
        return ""

    start_idx += len(start_header_norm)

    if end_header:
        end_header_norm = normalize_header(end_header).lower()
        end_idx = normalized_text.lower().find(end_header_norm, start_idx)
    else:
        end_idx = len(normalized_text)

    if end_idx == -1:
        end_idx = len(normalized_text)

    return normalized_text[start_idx:end_idx].strip()


def find_section_pages(
    pages: List[str],
    start_header: str,
    end_header: Optional[str]
) -> List[Optional[int]]:

    start_page, end_page = None, None
    total_pages = len(pages)

    start_header_norm = normalize_header(start_header).lower()
    end_header_norm = normalize_header(end_header).lower() if end_header else None

    for i, page_text in enumerate(pages):
        page_norm = normalize_pdf_text(page_text).lower()

        if start_page is None and start_header_norm in page_norm:
            start_page = i + 1

        if start_page and end_header_norm and end_header_norm in page_norm:
            end_page = i + 1
            break

    if start_page is None:
        return [None, None]

    if end_page is None:
        end_page = total_pages

    return [start_page, end_page]

def fill_sections_with_pages(
    pages: List[str],
    section_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fully hierarchy-aware, PDF-robust extraction.
    """

    headers = get_all_headers(section_dict)
    boundaries = compute_boundaries(headers)

    # Normalize full document once
    pdf_text = "\n\n".join(pages)
    normalized_text = normalize_pdf_text(pdf_text)

    def fill(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}

        for k, v in d.items():
            boundary = boundaries.get(k)

            content = extract_between(
                normalized_text,
                k,
                boundary
            )

            pages_range = find_section_pages(
                pages,
                k,
                boundary
            )

            if isinstance(v, dict) and v:
                result[k] = {
                    "content": content,
                    "pages": pages_range,
                    "subsections": fill(v)
                }
            else:
                result[k] = {
                    "content": content,
                    "pages": pages_range
                }

        return result

    return fill(section_dict)


def simplify_json(data: dict) -> dict:
    """
    Recursively simplify a nested JSON-like dictionary structure.

    This function traverses the input dictionary and simplifies it by:
    - Flattening any dictionary that contains exactly the keys `"content"` and `"pages"`,
      replacing it with the value of `"content"`.
    - Recursively processing nested dictionaries to apply the same rule at all levels.

    Args:
        data (dict): The input JSON-like dictionary to simplify.

    Returns:
        dict: A simplified version of the input dictionary with
              unnecessary nesting removed.
    
    Example:
        >>> sample = {
        ...     "Section 1": {"content": "Introduction text", "pages": [1, 2]},
        ...     "Section 2": {"Subsection": {"content": "Details", "pages": [3]}}
        ... }
        >>> simplify_json(sample)
        {'Section 1': 'Introduction text', 'Section 2': {'Subsection': 'Details'}}
    """
    simplified = {}
    for key, value in data.items():
        if isinstance(value, dict):
            # If it has 'content' and 'pages' keys — flatten it
            if set(value.keys()) == {"content", "pages"}:
                simplified[key] = value.get("content", "")
            else:
                # Recurse for nested dictionaries
                simplified[key] = simplify_json(value)
        else:
            simplified[key] = value
    return simplified

def format_markdown(all_responses: Union[list[ChunkResult2], list[ChunkResult3], list[ChunkResult], list[ChunkResult4]]) -> dict[str, str]:
    """
    Returns a dict where:
        key = last field name (e.g., 'study_type'),
        value = markdown string summarizing extracted_text, page_number, and context.
    Supports both ChunkResult2 (with ExtractedField) and ChunkResult3 (with FieldResult).
    """
    field_data = {}

    def collect(path: str, subobj):
        """Recursively collect page_number, context, extracted_text from nested models"""
        # Handle both FieldResult and ExtractedField
        if isinstance(subobj, (FieldResult, ExtractedField)):
            if subobj.extracted_text:
                key = path.split("/")[-1]

                # Special case for endpoint field
                if key == "endpoint":
                    keys_to_add = ["primary_endpoint", "secondary_endpoint"]
                else:
                    keys_to_add = [key]

                for k in keys_to_add:
                    results = field_data.setdefault(k, [])
                    results.append({
                        "text": subobj.extracted_text,
                        "page": getattr(subobj, "page_number", None),
                        "context": getattr(subobj, "context", None)
                    })

        elif isinstance(subobj, list):
            for item in subobj:
                collect(path, item)

        elif isinstance(subobj, BaseModel):
            for name, value in subobj:
                collect(f"{path}/{name}", value)

        elif isinstance(subobj, dict):
            for k, v in subobj.items():
                collect(f"{path}/{k}", v)

    # Walk through all responses (ChunkResult2 or ChunkResult3)
    for resp in all_responses:
        for field_name in resp.model_fields.keys():
            collect(field_name, getattr(resp, field_name, None))

    def clean_text(value: str) -> str:
        if not isinstance(value, str):
            return value
        return re.sub(r'[\x00-\x1f\x7f]', '', value).strip()
    
    # Build Markdown output
    markdown_output = {}
    for field, entries in field_data.items():
        clean_field = clean_text(field)
        md_lines = [f"## {clean_field}\n"]

        for idx, entry in enumerate(entries, 1):
            clean_text_value = clean_text(entry.get('text', ''))
            clean_context = clean_text(entry.get('context', ''))
            clean_page = clean_text(entry.get('page', ''))

            md_lines.append(f"**Content {idx}**")
            md_lines.append(f"- Extracted Text: {clean_text_value}")
            if clean_context:
                md_lines.append(f"- Context: {clean_context}")
            if clean_page:
                md_lines.append(f"- Page Number: {clean_page}\n")

        markdown_output[clean_field] = "\n".join(md_lines)
    return markdown_output

def format_predefined_list() -> str:
    """
    Load and format a predefined vendor-service list from a JSON file.

    This function reads a JSON file located at:
        <current working directory>/data/predefined_list.json

    The JSON is expected to be a dictionary where:
        - Keys are vendor categories (str)
        - Values are lists of services (List[str])

    The function formats this dictionary into a Markdown string
    with nested bullet points for each vendor and its services.

    Returns:
        str: A Markdown-formatted string of the predefined list.
    """
    # Load JSON file
    with open(os.path.join(os.getcwd(), 'data', 'predefined_list.json'), 'r') as f:
        data: Dict[str, List[str]] = json.load(f)

    # Extract predefined list (dict without Risks)
    predefined_list: Dict[str, List[str]] = {k: v for k, v in data.items()}

    # Format predefined list as nested bullet points
    predefined_list_md: str = "\n### Predefined List\n"
    for vendor, services in predefined_list.items():
        predefined_list_md += f"**Vendor Category: {vendor}**\n"
        predefined_list_md += f"**Description of Vendor: {services['description']}**\n"
        predefined_list_md += f"**Keywords**:\n"

        for s in services['keywords']:
            predefined_list_md += f"  - {s}\n"

    return predefined_list_md


def json_to_markdown(json_data: Dict[str, Any]) -> str:
    """
    Convert input contract JSON into a readable Markdown format.

    Sections included:
    ------------------
    • Terms  
    • Current Rebate  
    • Contract End Date  
    • Other Information (if available)

    Args:
        json_data (dict): Raw contract terms and metadata.

    Returns:
        str: Markdown-formatted text.
    """

    md = ""

    # ---- TERMS SECTION ----
    md += "### Terms\n"
    for term, value in json_data.get("Terms", {}).items():
        md += f"- **{term}**: {value}\n"

    # ---- BASIC CONTRACT FIELDS ----
    md += f"\n**Current Rebate:** {json_data.get('Current Rebate')}\n"
    md += f"**Contract End Date:** {json_data.get('Contract End Date')}\n"

    # ---- OTHER INFORMATION SECTION ----
    other_info = json_data.get("Other Information", {})
    if other_info:
        md += "\n### Other Information\n"
        for k, v in other_info.items():
            md += f"- **{k}**: {v}\n"

    return md

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))


    
METADATA_KEYS = {"extracted_text", "page_number", "context"}

def restore_from_reference(original, cleaned):
    """
    Restore missing metadata keys in `cleaned` JSON
    using `original` JSON as the reference.
    """

    if isinstance(original, dict) and isinstance(cleaned, dict):
        for key, original_value in original.items():
            
            # If metadata key is missing in cleaned → restore it
            if key in METADATA_KEYS and key not in cleaned:
                cleaned[key] = original_value

            # If key exists in both → recurse
            elif key in cleaned:
                restore_from_reference(original_value, cleaned[key])
            
            elif key == 'endpoint' and (f"primary_{key}" in cleaned or f"secondary_{key}" in cleaned):
                restore_from_reference(original_value, cleaned[f"primary_{key}"])
                restore_from_reference(original_value, cleaned[f"secondary_{key}"])


    elif isinstance(original, list) and isinstance(cleaned, list):
        for o_item, c_item in zip(original, cleaned):
            restore_from_reference(o_item, c_item)

    return cleaned


def collapse_sections(data: Any) -> Dict[str, Dict[str, List[Any]]]:
    result = defaultdict(lambda: {
        "page_number": [],
        "context": [],
        "extracted_text": []
    })

    def recurse(node: Any, current_key: str | None = None):
        if isinstance(node, dict):
            # check if this dict directly contains extractable content
            if METADATA_KEYS & node.keys() and current_key:
                for k in METADATA_KEYS:
                    if k in node:
                        result[current_key][k].append(node[k])

            for k, v in node.items():
                # move semantic key downwards
                recurse(v, k)

        elif isinstance(node, list):
            for item in node:
                recurse(item, current_key)

    # normalize input
    if isinstance(data, dict):
        data = [data]

    for obj in data:
        recurse(obj)

    return {
        k: v for k, v in result.items()
        if any(v.values())
    }


def flatten_sections(data):
    """
    Converts nested 'subsections' structure into flat structure:
    - Removes 'subsections' key
    - Promotes subsections directly under parent section
    - Preserves content and pages
    """

    def extract_sections(section_dict):
        flat_dict = {}

        for title, value in section_dict.items():
            # Add current section (without subsections)
            flat_dict[title] = {
                k: v for k, v in value.items()
                if k != "subsections"
            }

            # Recursively extract subsections
            if "subsections" in value and isinstance(value["subsections"], dict):
                flat_dict.update(extract_sections(value["subsections"]))

        return flat_dict

    final_output = {}

    for main_section, content in data.items():
        final_output[main_section] = extract_sections({main_section: content})

    return final_output
