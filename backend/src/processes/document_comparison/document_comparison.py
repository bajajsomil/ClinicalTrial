import asyncio
from config.config import Config
from collections import defaultdict
from typing import List, Tuple, Dict, Any
from src.adapters.azure_openai import batch_client
from src.adapters.logger import log_with_span
from src.processes.document_comparison.prompts.user_prompt import *
from src.utils import extract_pdf_pages, identify_index_pages, extract_sections
from src.processes.document_comparison.prompts.system import get_prompt_template
from src.processes.document_comparison.models import ProcessSectionResponse, ComparisonResult
from src.utils_helper import nested_set, timing_decorator, fill_sections_with_pages, remove_numbers_from_section, clean_json, simplify_json, flatten_sections


def json_to_markdown(data, indent=0):
    md = ""
    indent_str = "  " * indent 

    if isinstance(data, dict):
        for key, value in data.items():
            md += f"{indent_str}- **{key}**:\n"
            md += json_to_markdown(value, indent + 1)
    elif isinstance(data, list):
        for item in data:
            md += f"{indent_str}- "
            if isinstance(item, (dict, list)):
                md += "\n" + json_to_markdown(item, indent + 1)
            else:
                md += f"{item}\n"
    else:
        md += f"{indent_str}{data}\n"

    return md

async def collect_differences(
    dict1: Dict[str, Any],
    dict2: Dict[str, Any],
    parent_path: List[str] | None = None
) -> Tuple[
    List[Tuple[List[str], Any, Any]],
    List[Tuple[List[str], Any]],
    List[Tuple[List[str], Any]]
]:

    if parent_path is None:
        parent_path = []

    span_name = f"Document Comparison - Path: {'/'.join(parent_path) if parent_path else 'root'}"


    differences: List[Tuple[List[str], Any, Any]] = []
    new_sections: List[Tuple[List[str], Any]] = []
    removed_sections: List[Tuple[List[str], Any]] = []

    try:
        # Iterate over keys in dict1 → check modified or removed
        for key in dict1:
            current_path = parent_path + [key]
            current_span = f"Document Comparison - Path: {'/'.join(current_path)}"

            if key in dict2:
                val1, val2 = dict1[key], dict2[key]

                if isinstance(val1, dict) and isinstance(val2, dict):
                    # RECURSION LOG
                    log_with_span(
                        level="info",
                        message=f"Entering nested dictionary for key '{key}'",
                        span_name=current_span,
                        log_extra={
                            "service_name": "Document Comparison",
                            "api_name": "Document-Comparison",
                            "input": {"path": current_path},
                            "output": None,
                            "status": "in-progress"
                        }
                    )
                    nested_diffs, nested_new, nested_removed = await collect_differences(
                        val1, val2, current_path
                    )
                    differences.extend(nested_diffs)
                    new_sections.extend(nested_new)
                    removed_sections.extend(nested_removed)

                else:
                    # Compare leaf values
                    if str(val1).strip() != str(val2).strip():
                        differences.append((current_path, val1, val2))

                        log_with_span(
                            level="info",
                            message="Difference found",
                            span_name=current_span,
                            log_extra={
                                "service_name": "Document Comparison",
                                "api_name": "Document-Comparison",
                                "input": {"old": val1, "new": val2},
                                "output": {"difference": True},
                                "status": "in-progress"
                            }
                        )
                    else:
                        log_with_span(
                            level="info",
                            message="Values match",
                            span_name=current_span,
                            log_extra={
                                "service_name": "Document Comparison",
                                "api_name": "Document-Comparison",
                                "input": {"old": val1, "new": val2},
                                "output": {"difference": False},
                                "status": "in-progress"
                            }
                        )

            else:
                # Key removed
                removed_sections.append((current_path, dict1[key]))
                log_with_span(
                    level="info",
                    message="Key removed",
                    span_name=current_span,
                    log_extra={
                        "service_name": "Document Comparison",
                        "api_name": "Document-Comparison",
                        "input": {"key": key},
                        "output": {"removed_value": dict1[key]},
                        "status": "in-progress"
                    }
                )

        # Identify new keys present only in dict2
        for key in dict2:
            if key not in dict1:
                current_path = parent_path + [key]
                current_span = f"Document Comparison - Path: {'/'.join(current_path)}"
                val2 = dict2[key]

                if isinstance(val2, dict):
                    _, nested_new, _ = await collect_differences({}, val2, current_path)
                    new_sections.extend(nested_new)
                else:
                    new_sections.append((current_path, val2))

                log_with_span(
                    level="info",
                    message="New key added",
                    span_name=current_span,
                    log_extra={
                        "service_name": "Document Comparison",
                        "api_name": "Document-Comparison",
                        "input": {"key": key},
                        "output": {"new_value": val2},
                        "status": "in-progress"
                    }
                )

        # SUCCESS LOG
        log_with_span(
            level="info",
            message="Comparison completed for this level",
            span_name=span_name,
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"path": parent_path},
                "status": "success"
            }
        )

    except Exception as e:
        log_with_span(
            level="error",
            message="Error during comparison",
            span_name=span_name,
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"path": parent_path},
                "output": None,
                "status": "failed",
                "error": str(e)
            }
        )
        raise

    return differences, new_sections, removed_sections

async def process_difference(
    section_path: List[str],
    val1: Any,
    val2: Any
) -> ProcessSectionResponse:
    span_name = "Process Difference"
    section_name = " -> ".join(section_path)

    try:

        # Prepare section text blocks
        val1_text = f"### Section: {section_name}\n{val1}"
        val2_text = f"### Section: {section_name}\n{val2}"

        # Load system prompt
        system_prompt = get_prompt_template("impact_analysis_prompt.jinja2").render()

        # User prompt
        user_prompt = impact_analysis_prompt.format(
            first_version=val1_text,
            second_version=val2_text
        )

        # -------------------------------
        # Call LLM
        # -------------------------------
        response = await batch_client._process_single_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            model=Config.GPT_GENERATION_4O_MODEL,
            convert_to_json=True
        )

        # Extract content
        result = response.content

        # Build nested dictionary structure
        nested_result: Dict[str, Any] = {}
        current = nested_result
        for key in section_path[:-1]:
            current[key] = {}
            current = current[key]
        current[section_path[-1]] = result

        # -------------------------------
        # SUCCESS LOG
        # -------------------------------
        log_with_span(
            span_name=span_name,
            message=f"Successfully processed difference for {section_name} usign Azure OpenAI",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"system_prompt":system_prompt,
            "user_prompt":user_prompt},
                "output": result,
                "status": "completed"
            }
        )

        return ProcessSectionResponse(
            nested_result=nested_result,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
        )

    except Exception as e:

        # -------------------------------
        # ERROR LOG
        # -------------------------------
        log_with_span(
            span_name=span_name,
            message=f"Error processing difference for section: {section_name}",
            level="error",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {
                    "section_path": section_path,
                    "value 1": val1,
                    "value 2": val2
                },
                "status": "error",
                "error": str(e)
            }
        )

        # --------------------------------
        # RETURN EMPTY RESULT (NO RAISE)
        # --------------------------------
        empty_nested = {}
        current = empty_nested
        for key in section_path[:-1]:
            current[key] = {}
            current = current[key]
        current[section_path[-1]] = {}   # return empty object for failed section

        return ProcessSectionResponse(
            nested_result=empty_nested,
            input_tokens=0,
            output_tokens=0,
            model=None,
        )


async def process_section(
    key: List[str],
    value: Any,
    section_type: str
) -> Tuple[Any, int, int, str]:

    section_name = " -> ".join(key)
    span_name = "Process Section"

    try:
       
        # Render model instructions
        system_prompt = get_prompt_template(
            "section_added_or_removed_prompt.jinja2"
        ).render()

        # Build user prompt
        user_prompt = section_added_or_removed_prompt.format(
            added_or_removed=section_type,
            section_name=section_name,
            content=value
        )

        # ---------------------------------------------------------
        # CALL LLM
        # ---------------------------------------------------------
        response = await batch_client._process_single_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            model=Config.GPT_GENERATION_4i,
            convert_to_json=True
        )

        # ---------------------------------------------------------
        # SUCCESS SPAN LOG
        # ---------------------------------------------------------
        log_with_span(
            span_name=span_name,
            message=f"Successfully processed section: {section_name}",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"system_prompt":system_prompt,
            "user_prompt":user_prompt},
                "output": response.content,
                "status": "completed"
            }
        )

        return (
            response.content,
            response.input_tokens,
            response.output_tokens,
            response.model
        )

    except Exception as e:

        # ---------------------------------------------------------
        # ERROR SPAN LOG
        # ---------------------------------------------------------
        log_with_span(
            span_name=span_name,
            message=f"Error processing section: {section_name}",
            level="error",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {
                    "section_path": key,
                    "section_type": section_type,
                    "value": value
                },
                "status": "error",
                "error": str(e)
            }
        )

        return {'Impact': ''}, 0, 0, ""

async def section_added_or_removed(
    new_sections: List[Tuple[List[str], Any]],
    removed_sections: List[Tuple[List[str], Any]]
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, int]]]:

    span_name = "Process Added and Removed Sections"

    tasks: List[asyncio.Task] = []
    section_mapping: List[Tuple[str, List[str]]] = []

    try:
        # Prepare tasks
        for sections, section_type in [(new_sections, "added"), (removed_sections, "removed")]:
            for path, value in sections:
                tasks.append(process_section(path, value, section_type))
                section_mapping.append((section_type, path))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        result_dict: Dict[str, Any] = {"added": {}, "removed": {}}
        token_per_model: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0}
        )

        # Map responses
        for idx, response in enumerate(responses):
            section_type, path = section_mapping[idx]

            # Handle individual section failures
            if isinstance(response, Exception):
                err_msg = str(response)

                log_with_span(
                    span_name="Process Individual Section",
                    message=f"Error in processing section: {' -> '.join(path)}",
                    level="error",
                    log_extra={
                        "service_name": "Document Comparison",
                        "api_name": "Document-Comparison",
                        "input": {
                            "section_path": path,
                            "section_type": section_type
                        },
                        "status": "error",
                        "error": err_msg
                    }
                )

                nested_set(result_dict[section_type], path, {})
                continue

            # Successful response
            try:
                result, input_tokens, output_tokens, model = response
                nested_set(result_dict[section_type], path, result)
                
                token_per_model[model]["input_tokens"] += input_tokens
                token_per_model[model]["output_tokens"] += output_tokens

            except Exception as e:
                err_msg = str(e)

                log_with_span(
                    span_name="Process Individual Section",
                    message=f"Unexpected error mapping response for section: {' -> '.join(path)}",
                    level="error",
                    log_extra={
                        "service_name": "Document Comparison",
                        "api_name": "Document-Comparison",
                        "input": {
                            "section_path": path,
                            "section_type": section_type
                        },
                        "status": "error",
                        "error": err_msg
                    }
                )

                nested_set(result_dict[section_type], path, {})

        # -------------------------------------------------------------
        # SUCCESS SPAN
        # -------------------------------------------------------------
        log_with_span(
            span_name=span_name,
            message="Completed processing added and removed sections",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "status": "completed"
            }
        )

        return result_dict, dict(token_per_model)

    except Exception as e:
        err_msg = str(e)

        # -------------------------------------------------------------
        # CRITICAL ERROR SPAN
        # -------------------------------------------------------------
        log_with_span(
            span_name=span_name,
            message="Critical error in processing all sections",
            level="error",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "status": "error",
                "error": err_msg
            }
        )

        return {"added": {}, "removed": {}}, {}

async def compare_dicts_async(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> ComparisonResult:
    """
    Compare two nested dictionaries asynchronously using LLM-powered analysis.
    """
    span_name = "compare-dicts-async"

    try:

        # Step 1: Identify structural differences between dict1 and dict2
        diff_span = "collect-differences"
        differences, new_sections, removed_sections = await collect_differences(dict1, dict2)
        
        log_with_span(
            span_name=diff_span,
            message="Collected structural differences",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"JSON 1": dict1, "JSON 2": dict2},
                "status": "completed",
            }
        )

        # Step 2: Create async tasks
        diff_tasks = [process_difference(path, v1, v2) for path, v1, v2 in differences]
        sections_task = section_added_or_removed(new_sections, removed_sections)


        # Step 3: Run tasks concurrently
        span_name_run = "run-async-tasks"
        results_list, (results_list2, model_tokens2) = await asyncio.gather(
            asyncio.gather(*diff_tasks),
            sections_task
        )

        log_with_span(
            span_name=span_name_run,
            message="Async tasks completed",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": f"Total process difference tasks, Total section addition removal tasks",
                "status": "completed"
            }
        )

        final_result: Dict[str, Any] = {}
        model_tokens: Dict[str, Dict[str, int]] = {}

       
        def merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> None:
            for k, v in d2.items():
                if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                    merge(d1[k], v)
                else:
                    d1[k] = v

        for res in results_list:
            merge(final_result, res.nested_result)
            if res.model not in model_tokens:
                model_tokens[res.model] = {"input_tokens": 0, "output_tokens": 0}
            model_tokens[res.model]["input_tokens"] += res.input_tokens
            model_tokens[res.model]["output_tokens"] += res.output_tokens


    
        for model, tokens in model_tokens2.items():
            if model not in model_tokens:
                model_tokens[model] = {"input_tokens": 0, "output_tokens": 0}

            model_tokens[model]["input_tokens"] += tokens["input_tokens"]
            model_tokens[model]["output_tokens"] += tokens["output_tokens"]

       

        # Step 6: return final structured result
        span_name_return = "return-final-result"
        comparison_result = ComparisonResult(
            differences=final_result,
            section_added_or_removed_impact=results_list2,
            model_tokens=model_tokens
        )

        log_with_span(
            span_name=span_name_return,
            message="Dictionary comparison completed successfully",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"JSON 1": dict1, "JSON 2": dict2},
                "status": "success"
            }
        )

        return comparison_result

    except Exception as e:
        log_with_span(
            span_name="compare-dicts-async",
            message="Error during dictionary comparison",
            level="error",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"JSON 1": dict1, "JSON 2": dict2},
                "status": "failed",
                "error": str(e)
            }
        )
        raise

@timing_decorator
async def main_document_comparison(
    websocket,
    pdfpath1: str,
    pdfpath2: str
) -> Tuple[Dict[str, Any], List[List[str]], List[List[str]], Dict[str, Dict[str, int]]]:

    try:
    

        model_tokens: Dict[str, Dict[str, int]] = {}
        await websocket.send_json({
            "type": "progress",
            "step": "extract_pages",
            "message": "Extracting pages from documents...",
            "progress": 10
        })
        # -------------------------------------------------------------------
        # 1. Extract PDF pages
        # -------------------------------------------------------------------
        span_extract = "extract-pdf-pages"
        pages1_task = extract_pdf_pages(pdfpath1)
        pages2_task = extract_pdf_pages(pdfpath2)
        (pdf1, _), (pdf2, _) = await asyncio.gather(pages1_task, pages2_task)
        await websocket.send_json({
            "type": "progress",
            "step": "extract_pages_complete",
            "message": f"Extracted {len(pdf1.pages)} pages from document 1 and {len(pdf2.pages)} pages from document 2",
            "progress": 25
        })
        await websocket.send_json({
            "type": "progress",
            "step": "identify_index",
            "message": "Identifying table of contents...",
            "progress": 30
        })
        log_with_span(
            span_name=span_extract,
            message="Extracted pages from PDFs",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"pdfpath1": pdfpath1, "pdfpath2": pdfpath2},
                "status": "completed"
            }
        )

        # -------------------------------------------------------------------
        # 2. Identify index pages using LLM
        # -------------------------------------------------------------------
        span_index = "identify-index-pages"
        index1_task = identify_index_pages(pdf1.pages)
        index2_task = identify_index_pages(pdf2.pages)
        (index1, in_t1, out_t1, model1), (index2, in_t2, out_t2, model2) = await asyncio.gather(
            index1_task, index2_task
        )

        for m, i_t, o_t in [(model1, in_t1, out_t1), (model2, in_t2, out_t2)]:
            model_tokens.setdefault(m, {"input_tokens": 0, "output_tokens": 0})
            model_tokens[m]["input_tokens"] += i_t
            model_tokens[m]["output_tokens"] += o_t
        await websocket.send_json({
            "type": "progress",
            "step": "identify_index_complete",
            "message": "Table of contents identified",
            "progress": 40
        })
        await websocket.send_json({
            "type": "progress",
            "step": "extract_sections",
            "message": "Extracting document sections...",
            "progress": 50
        })
        log_with_span(
            span_name=span_index,
            message="Identified index pages",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"pdfpath1": pdfpath1, "pdfpath2": pdfpath2},
                "output": {
                    "index1_range": [index1.start_page, index1.end_page],
                    "index2_range": [index2.start_page, index2.end_page]
                },
                "status": "completed"
            }
        )

        # -------------------------------------------------------------------
        # 3. Extract hierarchical sections
        # -------------------------------------------------------------------
        span_sections = "extract-sections"
        sections1_task = extract_sections(pdf1.pages, index1)
        sections2_task = extract_sections(pdf2.pages, index2)
        (sections1, in_t1, out_t1, model1), (sections2, in_t2, out_t2, model2) = await asyncio.gather(
            sections1_task, sections2_task
        )
        await websocket.send_json({
            "type": "data",
            "step": "sections_extracted",
            "message": "Sections extracted successfully",
            "progress": 60,
            "data": {
               "pdf1_sections": [s.dict() if hasattr(s, "dict") else s for s in sections1.sections],
                "pdf2_sections": [s.dict() if hasattr(s, "dict") else s for s in sections2.sections]
            }
        })
        await websocket.send_json({
            "type": "progress",
            "step": "fill_sections",
            "message": "Analyzing section content...",
            "progress": 70
        })

        for m, i_t, o_t in [(model1, in_t1, out_t1), (model2, in_t2, out_t2)]:
            model_tokens.setdefault(m, {"input_tokens": 0, "output_tokens": 0})
            model_tokens[m]["input_tokens"] += i_t
            model_tokens[m]["output_tokens"] += o_t

        log_with_span(
            span_name=span_sections,
            message="Extracted hierarchical sections",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"index1": index1, "index2": index2},
                "output": {
                    "sections_pdf1": sections1.sections,
                    "sections_pdf2": sections2.sections,
                },
                "status": "success"
            }
        )

        # -------------------------------------------------------------------
        # 4. Fill sections with page text
        # -------------------------------------------------------------------
        empty_pages1, empty_pages2 = [], []

        for i, page in enumerate(pdf1.pages, start=1):
            empty_pages1.append("" if index1.start_page <= i <= index1.end_page else page)

        for i, page in enumerate(pdf2.pages, start=1):
            empty_pages2.append("" if index2.start_page <= i <= index2.end_page else page)

        filled1 = simplify_json(flatten_sections(fill_sections_with_pages(empty_pages1, sections1.sections)))
        filled2 = simplify_json(flatten_sections(fill_sections_with_pages(empty_pages2, sections2.sections)))
        await websocket.send_json({
            "type": "progress",
            "step": "normalize_sections",
            "message": "Normalizing section headers...",
            "progress": 80
        })

        # -------------------------------------------------------------------
        # 5. Clean section headers
        # -------------------------------------------------------------------
        span_clean = "Filled sections"
        cleaned_filled1 = remove_numbers_from_section(filled1)
        cleaned_filled2 = remove_numbers_from_section(filled2)

        log_with_span(
            span_name=span_clean,
            message="filled all sections with their data from pdf",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "input": {"section1": sections1.sections, "section2": sections2.sections},
                "output": {"Filled1": cleaned_filled1, "Filled2": cleaned_filled2},
                "api_name": "Document-Comparison",
                "status": "success"
            }
        )

        # -------------------------------------------------------------------
        # 6. Compare dictionaries using LLM
        # -------------------------------------------------------------------
        span_compare = "compare-cleaned-dicts"
        final_result_model: ComparisonResult = await compare_dicts_async(cleaned_filled1, cleaned_filled2)
        result_dict = final_result_model.dict()
        await websocket.send_json({
            "type": "progress",
            "step": "finalize",
            "message": "Finalizing comparison results...",
            "progress": 90
        })
        for m, tokens in result_dict.get("model_tokens", {}).items():
            model_tokens.setdefault(m, {"input_tokens": 0, "output_tokens": 0})
            model_tokens[m]["input_tokens"] += tokens["input_tokens"]
            model_tokens[m]["output_tokens"] += tokens["output_tokens"]

        log_with_span(
            span_name=span_compare,
            message="Completed semantic comparison using LLM",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "status": "success"
            }
        )

        # -------------------------------------------------------------------
        # 7. Create human-readable Markdown + Summary
        # -------------------------------------------------------------------
        span_summary = "generate-summary"

        final_impact_analysis = clean_json(result_dict["differences"])
        markdown_data = json_to_markdown({
            'differences': final_impact_analysis,
            'section_added_or_removed_impact': result_dict["section_added_or_removed_impact"]
        })

        user_prompt = f"Comparison:\n\n {markdown_data}"
        summary_prompt = get_prompt_template('document_comparison_summary.jinja2').render()
        summary = await batch_client._process_single_request(
            system_prompt=summary_prompt,
            user_prompt=user_prompt
        )
        model_tokens.setdefault(summary.model, {"input_tokens": 0, "output_tokens": 0})
        model_tokens[summary.model]["input_tokens"] += summary.input_tokens
        model_tokens[summary.model]["output_tokens"] += summary.output_tokens


        log_with_span(
            span_name=span_summary,
            message="Generated document comparison summary",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": { "system_prompt":summary_prompt,
            "user_prompt":user_prompt},
            "output": summary.content,
                "status": "success"
            }
        )

        # -------------------------------------------------------------------
        # FINAL SUCCESS RETURN
        # -------------------------------------------------------------------
        span_return = "main-document-comparison-return"
        log_with_span(
            span_name=span_return,
            message="Document comparison pipeline finished successfully",
            level="info",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"pdfpath1": pdfpath1, "pdfpath2": pdfpath2},
                "output": {"final_impact_analysis": final_impact_analysis, 
                           "section_added_or_removed_impact": result_dict["section_added_or_removed_impact"],
                           "summary": summary.content},
                "status": "success"
            }
        )
        await websocket.send_json({
            "type": "complete",
            "step": "complete",
            "message": "Comparison complete!",
            "progress": 100,
            "data": { "differences": final_impact_analysis, "new_sections": result_dict["section_added_or_removed_impact"], "model_tokens": model_tokens }
            
        })
        import json

        with open("token_usage.json", "w") as f:
            json.dump(model_tokens, f, indent=4)
        return final_impact_analysis, result_dict["section_added_or_removed_impact"], model_tokens

    except Exception as e:
        # -------------------------------------------------------------------
        # ERROR LOG
        # -------------------------------------------------------------------
        log_with_span(
            span_name="main-document-comparison-error",
            message="Error during document comparison pipeline",
            level="error",
            log_extra={
                "service_name": "Document Comparison",
                "api_name": "Document-Comparison",
                "input": {"pdfpath1": pdfpath1, "pdfpath2": pdfpath2},
                "status": "error",
                "error": str(e)
            }
        )
        raise

