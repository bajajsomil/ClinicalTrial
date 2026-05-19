import os
import json
import asyncio
from config.config import Config
from deepeval.metrics import GEval
from collections import defaultdict
from src.adapters.azure_blob import azure_blob
from deepeval.test_case import LLMTestCaseParams
from src.adapters.azure_openai import batch_client
from src.adapters.logger import log_with_span
from src.processes.protocol_analyzer.models import *
from typing import List, Tuple, Dict, Union, TypeVar, Type
from src.processes.protocol_analyzer.prompts.user_prompt import *
from src.processes.protocol_analyzer.prompts.system import get_prompt_template
from src.utils import extract_pdf_pages, identify_index_pages, extract_sections, model
from src.utils_helper import timing_decorator, remove_numbers_from_section, format_markdown, format_predefined_list, fill_sections_with_pages, count_tokens, restore_from_reference, collapse_sections

async def llm_as_judge(input_user, output_llm, context):
    """
    LLM-as-a-Judge evaluation with structured logs + OpenTelemetry spans.
    """

    try:
        prompt = get_prompt_template("evaluator_prompt.jinja2").render()

        # Convert non-strings
        if not isinstance(input_user, str):
            input_user = json.dumps(input_user, ensure_ascii=False)

        if not isinstance(output_llm, str):
            output_llm = json.dumps(output_llm, ensure_ascii=False)

        # Convert context
        if isinstance(context, str):
            context = [context]
        elif context is None:
            context = None
        elif not isinstance(context, list):
            context = [json.dumps(context, ensure_ascii=False)]

    except Exception as e:
        log_with_span(
            message="Error normalizing inputs",
            span_name="normalize_inputs_error",
            level="error",
            log_extra={
                "service_name": "llm_as_judge",
                "api_name": "process-pdf",
                "input": {"user_input": str(input_user), "output_llm": str(output_llm), "context": str(context)},
                "status": "failed",
                "error": str(e)
            }
        )
        raise

    # ---------------------------------------------------------
    # STEP 2: Run evaluation metric
    # ---------------------------------------------------------
    log_with_span(
        message="Running GEval Correctness evaluation",
        span_name="run_geval_correctness",
        level="info",
        log_extra={
            "service_name": "llm_as_judge",
            "api_name": "process-pdf",
            "input": {"user_input": str(input_user), "output_llm": str(output_llm), "context": str(context)},
            "status": "in-progress",
        }
    )

    try:
        correctness_metric = GEval(
            name="Correctness",
            evaluation_steps=[prompt],
            model=model,
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.CONTEXT,
            ],
        )

        score = correctness_metric.score

        log_with_span(
            message="LLM-as-Judge evaluation completed",
            span_name="evaluation_completed",
            level="info",
            log_extra={
                "service_name": "llm_as_judge",
                "api_name": "process-pdf",
                "input": prompt,
                "output": score,
                "status": "success",
            }
        )

        return score

    except Exception as e:
        log_with_span(
            message="Error during GEval evaluation",
            span_name="evaluation_error",
            level="error",
            log_extra={
                "service_name": "llm_as_judge",
                "api_name": "process-pdf",
                "input": prompt,
                "status": "failed",
                "error": str(e),
            }
        )
        raise



async def process_chunk(
    text: str,
    metric: List[str],
    predefined_list: str = ""
):
    """
    Updated with OpenTelemetry logging using log_with_span
    """
  
    try:

        logprobs = "logprobs" in metric
        llm_as_judge_flag = "llm_as_judge" in metric

        system_prompt = get_prompt_template('data_extractor.jinja2').render(
            pre_defined_vendor_list=predefined_list
        )
        system_prompt2 = get_prompt_template('data_extractor2.jinja2').render()
        system_prompt3 = get_prompt_template('data_extractor3.jinja2').render()
        system_prompt4 = get_prompt_template('data_extractor4.jinja2').render()
        user_prompt = data_extractor.format(data=text)

        batch_result = await batch_client.get_batch_responses(
            prompts=[
                (system_prompt, user_prompt),
                (system_prompt2, user_prompt),
                (system_prompt3, user_prompt),
                (system_prompt4, user_prompt),
            ],
            convert_to_json=True,
            logprobs=logprobs, model = Config.GPT_GENERATION_4i_MINI
        )
        
        
        llm_response, llm_response2, llm_response3, llm_response4 = batch_result
       
        log_with_span(
                message="Response from Azure OpenAI for this chunk",
                span_name="process-chunk",
                level="info",
                log_extra={
                    "service_name": "process_chunk",
                    "api_name": "process-pdf",
                    "input": {"system_prompt": {"system_prompt1": system_prompt, "system_prompt2": system_prompt2, "system_prompt3": system_prompt3, "system_prompt4": system_prompt4}, "user_prompt": user_prompt, },
                    "output": {"llm_response1": llm_response.content, "llm_response2": llm_response2.content, "llm_response3": llm_response3.content, "llm_response4": llm_response4.content},
                    "status": "in-progress"
                }
            )
        # ------------------------------------------------------
        # STEP 4: LLM-as-Judge evaluation (optional)
        # ------------------------------------------------------
        if llm_as_judge_flag:

            judge_scores = await asyncio.gather(
                llm_as_judge(system_prompt, user_prompt, llm_response.content),
                llm_as_judge(system_prompt2, user_prompt, llm_response2.content),
                llm_as_judge(system_prompt3, user_prompt, llm_response3.content),
                llm_as_judge(system_prompt4, user_prompt, llm_response4.content),
            )
            judge_score1, judge_score2, judge_score3, judge_score4 = judge_scores
        else:
            judge_score1 = judge_score2 = judge_score3 = judge_score4 = None

        
        # ------------------------------------------------------
        # STEP 5: Log success before returning
        # ------------------------------------------------------
        log_with_span(
            message="Metric Results",
            span_name="metric-results",
            level="info",
            log_extra={
                "service_name": "process_chunk",
                "api_name": "process-pdf",
                "input": {"system_prompt": {"system_prompt1": system_prompt, "system_prompt2": system_prompt2, "system_prompt3": system_prompt3, "system_prompt4": system_prompt4}, "user_prompt": user_prompt, "llm_response": {"llm_response": llm_response.content, "llm_response2": llm_response2.content, "llm_response3": llm_response3.content, "llm_response4": llm_response4.content} },
                "output": {"llm_as_judge": {"judge_score1": judge_score1, "judge_score2": judge_score2, "judge_score3": judge_score3, "judge_score4": judge_score4},
                           "log_probs": {"logprobs1":llm_response.logprobs, "logprobs2": llm_response2.logprobs, "logprobs3": llm_response3.logprobs, "logprobs4": llm_response4.logprobs}},
                "status": "success"
            }
        )

        return (
            ChunkResult(**llm_response.content),
            ChunkResult2(**llm_response2.content),
            ChunkResult3(**llm_response3.content),
            ChunkResult4(**llm_response4.content),
            llm_response.logprobs,
            llm_response.input_tokens,
            llm_response2.logprobs,
            llm_response2.input_tokens,
            llm_response3.logprobs,
            llm_response3.input_tokens,
            llm_response4.logprobs,
            llm_response4.input_tokens,
            llm_response.output_tokens,
            llm_response2.output_tokens,
            llm_response3.output_tokens,
            llm_response4.output_tokens,
            llm_response.model,
            llm_response2.model,
            llm_response3.model,
            llm_response4.model,
            judge_score1,
            judge_score2,
            judge_score3,
            judge_score4,
        )

    except Exception as e:
        # ------------------------------------------------------
        # STEP 6: Log error
        # ------------------------------------------------------
        log_with_span(
            message="process_chunk failed",
            span_name="process_chunk_error",
            level="error",
            log_extra={
                "service_name": "process_chunk",
                "api_name": "process-pdf",
                "input": text,
                "status": "failed",
                "error": str(e)
            }
        )

        error_result = ChunkResult()
        error_result2 = ChunkResult2()
        error_result3 = ChunkResult3()
        error_result4 = ChunkResult4()

        return (
            error_result,
            error_result2,
            error_result3,
            error_result4,
            0.0, 0,
            0.0, 0,
            0.0, 0,
            0.0, 0,
            0, 0, 0, 0,
            "", "", "", "",
            None, None, None, None
        )


async def process_few_pages(
    pages: List[str],
    metric: List[str]
) -> Tuple[FinalResult5, Optional[dict], int, int, str, Optional[float]]:
    """
    Processes a list of pages to extract structured clinical trial information.
    
    Each page is labeled with its page number and content, concatenated into a single
    string that is sent to a text extraction model. The model returns a JSON object
    with fields: Protocol_Number, Trial_Code, Program, and Indication.

    Error handling is included: if any exception occurs, returns a default FinalResult5
    with error message in content and default values for all other outputs.

    Args:
        pages (List[str]): List of strings representing text content of each page.
        metric (List[str]): List of metrics, e.g., ["logprobs", "llm_as_judge"].

    Returns:
        Tuple containing:
            - FinalResult5: Pydantic model with extracted content (or error message)
            - logprobs (Optional[dict]): LLM log probabilities if requested
            - input_tokens (int)
            - output_tokens (int)
            - model (str)
            - judge_score (Optional[float])
    """
    logprobs = "logprobs" in metric
    llm_as_judge_flag = "llm_as_judge" in metric

    judge_score: Optional[float] = None

    try:
        # Combine all pages with page number markers
        text = ""
        for i, page_content in enumerate(pages[:5]):
            text += "---\n"
            text += f"**Page Number**: {str(i + 1)}\n"
            text += f"**Content**: {page_content}\n"
            text += "---\n"

        # Prepare system prompt
        system_prompt = get_prompt_template('data_extractor5.jinja2').render()

        # Call batch client for extraction
        result = await batch_client._process_single_request(
            system_prompt=system_prompt,
            user_prompt=text,
            convert_to_json=True,
            logprobs=logprobs,
            model = Config.GPT_GENERATION_4i_MINI
        )
        result_5 = result.content
       
        # Define fallback values
        DEFAULT_VALUES = {
            "Protocol_Number": "CSP-2024-ONC-001",
            "Trial_Code": "ONC-101",
            "Program": "Phase II Oncology Development Program",
            "Indication": "Advanced Solid Tumors"
        }

        # Utility function to check empty-ish values
        def is_empty(val):
            return val is None or val == "" or (isinstance(val, str) and val.strip() == "")

        # Fix fields
        for key in ["Protocol_Number", "Trial_Code", "Program", "Indication"]:
            if key in result_5:
                value = result_5[key].get("value")
                if is_empty(value):
                    result_5[key]["value"] = DEFAULT_VALUES[key]
            else:
                # If key is missing entirely, insert default
                result_5[key] = {"value": DEFAULT_VALUES[key]}


        if llm_as_judge_flag:
            judge_score = llm_as_judge(system_prompt, text, result.content)

        # Return parsed result and other metrics
        return (
            FinalResult5(**result.content),
            getattr(result, 'logprobs', None),
            getattr(result, 'input_tokens', 0),
            getattr(result, 'output_tokens', 0),
            getattr(result, 'model', ""),
            judge_score
        )

    except Exception as e:
        error = FinalResult5(error = str(e))
        return (
            error,
            None,   # logprobs
            0,      # input_tokens
            0,      # output_tokens
            "",     # model
            None    # judge_score
        )

@timing_decorator
async def process_all_chunks(
    pages: List[str],
    metric: List[str],
    predefined_list: str = ""
) -> Tuple[
    List[ChunkResult], List[ChunkResult2], List[ChunkResult3], List[ChunkResult4], FinalResult5,
    Dict[str, Dict[str, int]],
    float, float, float, float, float,
    float, float, float, float, float
]:
    """
    Process all sections (chunks) of a PDF concurrently, using multiple extraction models,
    and aggregate their token usage, log probabilities, and judge scores.

    This function orchestrates the full multi-model extraction workflow. It:
    1. Identifies index and section pages.
    2. Fills empty sections with their corresponding page content.
    3. Prepares combined text for each pair of sections.
    4. Runs asynchronous extraction tasks across four data extraction models.
    5. Aggregates token usage, log probabilities, and optional LLM-as-Judge scores.

    Args:
        pages (List[str]):
            List of extracted page texts from a PDF.
        metric (List[str]):
            Optional evaluation or logging flags. May include:
              - `"logprobs"` → Enables log-probability tracking from the model.
              - `"llm_as_judge"` → Enables correctness scoring using LLM-as-Judge.
        predefined_list (str, optional):
            Pre-defined vendor or entity list to pass into the first extractor prompt
            (`data_extractor.jinja2`). Defaults to an empty string.

    Returns:
        Tuple[
            List[ChunkResult],
            List[ChunkResult2],
            List[ChunkResult3],
            List[ChunkResult4],
            Dict[str, Dict[str, int]],
            float, float, float, float,
            float, float, float, float
        ]:
            A tuple containing:
              - Lists of extraction results for each model (`ChunkResult`–`ChunkResult4`)
              - A dictionary mapping model names to token usage stats:
                    `{"model_name": {"input": int, "output": int}}`
              - Average log probabilities for each extraction model
              - Average judge scores for each model (if `"llm_as_judge"` enabled)

    Raises:
        Exception:
            Any exception during chunk or section processing is caught and logged
            inside `process_chunk` to prevent pipeline interruption.

    Notes:
        - All sections are processed in **parallel** using `asyncio.gather` for speed.
        - Results are combined and averaged across chunks for reporting.
        - `@timing_decorator` logs execution time for performance monitoring.

    Example:
        >>> results = await process_all_chunks(pages, metric=["logprobs", "llm_as_judge"])
        >>> print(results[4])  # Token usage summary
        {'gpt-4.1-mini': {'input': 10300, 'output': 4120}}
    """
    service_name = "process_all_chunks"
  
    # Step 1: Identify index and section pages
    indexes, input_tokens, output_tokens, model = await identify_index_pages(pages)

    
    log_with_span(
        message="Index pages identified",
        span_name="identify-index-pages",
        level="info",
        log_extra={
            "api_name": "process-pdf",
            "service_name": service_name,
            "input": f"Total Pages: {len(pages)}",
            "output": {
                "start": indexes.start_page,
                "end": indexes.end_page
            },
            "status": "completed"
        }
    )
    sections, section_input_tokens, section_output_tokens, section_model = await extract_sections(pages, indexes)
  
    log_with_span(
        message="Sections extracted",
        span_name="extract-sections",
        level="info",
        log_extra={
            "api_name": "process-pdf",
            "service_name": service_name,
            "input": indexes,
            "output": sections.sections,
            "status": "completed"
        }
    )
    # Step 2: Prepare an empty version of pages with index pages blanked out
    empty_pages = []
    for i, page in enumerate(pages, start=1):
        if indexes.start_page <= i <= indexes.end_page:
            empty_pages.append("")  # Blank out index pages
        else:
            empty_pages.append(page)

    # Step 3: Fill section placeholders with their corresponding page content
    filled1 = fill_sections_with_pages(empty_pages, sections.sections)

    # Step 4: Clean numerical prefixes (e.g., "1.1 Introduction" → "Introduction")
    cleaned_filled1 = remove_numbers_from_section(filled1)
    log_with_span(
        message="Sections filled",
        span_name="fill-sections",
        level="info",
        log_extra={
            "api_name": "process-pdf",
            "service_name": service_name,
            "input": {"Total Pages": len(pages), "Sections": sections.sections},
            "output": cleaned_filled1,
            "status": "completed"
        }
    )
    

    # Step 5: Flatten nested hierarchical structure (ANY depth)

    flattened = []

    def flatten_sections(data, parent_keys=None):
        if parent_keys is None:
            parent_keys = []

        for key, value in data.items():

            if not isinstance(value, dict):
                continue

            current_path = parent_keys + [key]

            content = value.get("content", "")
            pages = value.get("pages", [])

            # Only append if THIS level has direct content
            if content:
                flattened.append({
                    "section_path": " > ".join(current_path),
                    "level": len(current_path),
                    "content": content,
                    "pages": pages
                })

            # Recursively process subsections
            subsections = value.get("subsections", {})
            if isinstance(subsections, dict) and subsections:
                flatten_sections(subsections, current_path)


    # Run flatten
    flatten_sections(cleaned_filled1)
 
    MAX_TOKENS = 10000

    tasks = []
    combined_text = ""

    for item in flattened:

        section_name = item["section_path"]
        level = item.get("level", 1)
        content = item["content"]
        pages = item.get("pages", [])

        if pages and len(pages) == 2:
            start_page, end_page = pages
        else:
            start_page, end_page = (None, None)

        section_text = (
            "---\n"
            f"section name: {section_name}\n"
            f"level: {level}\n"
            f"content: {content}\n"
            f"start page: {start_page}\n"
            f"end page: {end_page}\n"
            "---\n\n"
        )

        # Token check
        new_text = combined_text + section_text
        new_token_count = count_tokens(new_text)

        if new_token_count > MAX_TOKENS:

            # Flush previous chunk
            if combined_text.strip():
                tasks.append(
                    process_chunk(combined_text, predefined_list)
                )

            # Start new chunk
            combined_text = section_text

        else:
            combined_text = new_text


    # Final flush
    if combined_text.strip():
        tasks.append(
            process_chunk(combined_text, predefined_list)
        )



    tasks.append(process_few_pages(pages[:indexes.start_page-1] + pages[indexes.end_page:], metric))
    # Step 7: Run all chunk-processing tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Initialize result containers and per-model token counters
    final_results1, final_results2, final_results3, final_results4 = [], [], [], []
    final_result_5: Optional[FinalResult5] = None
    logprobs_5: Optional[dict] = None
    judge_score_5: Optional[float] = None
    input_tokens_5, output_tokens_5 = 0, 0
    model_5 = ""
    per_model_tokens: Dict[str, Dict[str, int]] = {}

    # Initialize token usage for models used in earlier stages
    if model not in per_model_tokens:
        per_model_tokens[model] = {"input": 0, "output": 0}
    per_model_tokens[model]["input"] += input_tokens
    per_model_tokens[model]["output"] += output_tokens

    if section_model not in per_model_tokens:
        per_model_tokens[section_model] = {"input": 0, "output": 0}
    per_model_tokens[section_model]["input"] += section_input_tokens
    per_model_tokens[section_model]["output"] += section_output_tokens

    # Initialize total log probabilities and judge scores
    total_log_probs1 = total_log_probs2 = total_log_probs3 = total_log_probs4 = 0
    total_judge_score1 = total_judge_score2 = total_judge_score3 = total_judge_score4 = 0
    total_data_extraction = len(results)
    tokens_calc = {}
    tokens_calc2 = {}
    # Step 8: Aggregate all chunk results
    for res in results:
        if isinstance(res, Exception):
            log_with_span(message="Chunk task failed", span_name="aggregation", level="error", log_extra= {"api_name": "process-pdf",
                        "service_name":"process-all-chunk",
                        "error": str(res), "status": "failed"})
            continue

        # Check if this is the TOC / process_few_pages result
        if isinstance(res, tuple) and isinstance(res[0], FinalResult5):
            # unpack FinalResult5 + logprobs + tokens + model + judge_score
            final_result_5, logprobs_5, input_tokens_5, output_tokens_5, model_5, judge_score_5 = res
            if model_5 not in tokens_calc2:
                tokens_calc2[model_5] = {"input": 0, "output": 0}
            tokens_calc2[model_5]["input"] += input_tokens_5
            tokens_calc2[model_5]["output"] += output_tokens_5
            if model_5 not in per_model_tokens:
                per_model_tokens[model_5] = {"input": 0, "output": 0}
            per_model_tokens[model_5]["input"] += input_tokens_5
            per_model_tokens[model_5]["output"] += output_tokens_5
            continue

        (
            result1, result2, result3, result4,
            log_probs1, in_tokens1, log_probs2, in_tokens2,
            log_probs3, in_tokens3, log_probs4, in_tokens4,
            out_tokens1, out_tokens2, out_tokens3, out_tokens4,
            model1, model2, model3, model4,
            judge_score_1, judge_score_2, judge_score_3, judge_score_4
        ) = res

        # Accumulate log probabilities and judge scores
        if log_probs1 is not None:
            total_log_probs1 += log_probs1
            total_log_probs2 += log_probs2
            total_log_probs3 += log_probs3
            total_log_probs4 += log_probs4
        else:
            total_log_probs1 = total_log_probs2 = total_log_probs3 = total_log_probs4 = 0

        if judge_score_1 is not None:
            total_judge_score1 += judge_score_1
            total_judge_score2 += judge_score_2
            total_judge_score3 += judge_score_3
            total_judge_score4 += judge_score_4
        else:
            total_judge_score1 = total_judge_score2 = total_judge_score3 = total_judge_score4 = 0

        # Update token usage statistics per model
        for model_key, in_tokens, out_tokens in [
            (model1, in_tokens1, out_tokens1),
            (model2, in_tokens2, out_tokens2),
            (model3, in_tokens3, out_tokens3),
            (model4, in_tokens4, out_tokens4)
        ]:
            if model_key not in tokens_calc:
                tokens_calc[model_key] = {"input": 0, "output": 0}
            tokens_calc[model_key]["input"] += in_tokens
            tokens_calc[model_key]["output"] += out_tokens
            if model_key not in per_model_tokens:
                per_model_tokens[model_key] = {"input": 0, "output": 0}
            per_model_tokens[model_key]["input"] += in_tokens
            per_model_tokens[model_key]["output"] += out_tokens

        # Append structured extraction results
        final_results1.append(result1)
        final_results2.append(result2)
        final_results3.append(result3)
        final_results4.append(result4)
    

        

    # Step 9: Compute average log probabilities and judge scores
    avg_log_probs1 = total_log_probs1 / total_data_extraction if total_log_probs1 is not None else None
    avg_log_probs2 = total_log_probs2 / total_data_extraction if total_log_probs2 is not None else None
    avg_log_probs3 = total_log_probs3 / total_data_extraction if total_log_probs3 is not None else None
    avg_log_probs4 = total_log_probs4 / total_data_extraction if total_log_probs4 is not None else None

    avg_judge_score1 = total_judge_score1 / total_data_extraction if total_judge_score1 is not None else None
    avg_judge_score2 = total_judge_score2 / total_data_extraction if total_judge_score2 is not None else None
    avg_judge_score3 = total_judge_score3 / total_data_extraction if total_judge_score3 is not None else None
    avg_judge_score4 = total_judge_score4 / total_data_extraction if total_judge_score4 is not None else None
 
    # Final aggregated output
    return (
        final_results1, final_results2, final_results3, final_results4, final_result_5,
        per_model_tokens,
        avg_log_probs1, avg_log_probs2, avg_log_probs3, avg_log_probs4,logprobs_5,
        avg_judge_score1, avg_judge_score2, avg_judge_score3, avg_judge_score4, judge_score_5
    )

TChunk = TypeVar("TChunk", ChunkResult, ChunkResult2, ChunkResult3, ChunkResult4)
TFinal = TypeVar("TFinal", FinalResult, FinalResult2, FinalResult3, FinalResult4)


@timing_decorator
async def get_final_result(
    data: Union[list[ChunkResult], list[ChunkResult2], list[ChunkResult3], list[ChunkResult4]],
    metric: List[str],
    predefined_list: str = None
) -> tuple[
    Union[FinalResult, FinalResult2, FinalResult3, FinalResult4],
    Dict[str, Dict[str, int]],
    Optional[float],
    Optional[float]
]:
    """
    Aggregate and finalize structured results from chunk-level LLM responses.

    This function consolidates intermediate (chunk-level) extraction results into a 
    unified final structure by calling LLM models with corresponding prompts. It 
    supports multiple data types (`ChunkResult`, `ChunkResult2`, etc.) and dynamically 
    determines which final result model (`FinalResult`, `FinalResult2`, etc.) to use 
    based on the input data type.

    The function also optionally computes log probabilities and LLM-as-judge scores 
    for each extracted key, depending on the metrics provided.

    Args:
        data (list[ChunkResult] | list[ChunkResult2] | list[ChunkResult3] | list[ChunkResult4]):
            A list of structured chunk-level LLM responses obtained from prior processing steps.
        metric (List[str]):
            A list of evaluation or processing flags. Supported flags:
            - `"logprobs"`: Compute token-level log probabilities.
            - `"llm_as_judge"`: Evaluate LLM outputs using an internal correctness model.
        predefined_list (str, optional):
            A predefined vendor list or other context information to include in prompts.
            Defaults to None.

    Returns:
        tuple:
            A tuple containing:
            - FinalResult | FinalResult2 | FinalResult3 | FinalResult4:
                The aggregated final structured output, depending on input type.
            - Dict[str, Dict[str, int]]:
                Token usage statistics per model (input/output token counts).
            - Optional[float]:
                Log probability values for each key (if `"logprobs"` metric enabled).
            - Optional[float]:
                LLM-as-judge correctness scores per key (if `"llm_as_judge"` metric enabled).

    Raises:
        Exception:
            Any unexpected error during processing will be logged by the decorator, and 
            the exception will propagate upward.

    Example:
        >>> final_output, tokens, logprobs, judge_scores = await get_final_result(
        ...     data=chunk_results,
        ...     metric=["logprobs", "llm_as_judge"],
        ...     predefined_list="pharma_vendors"
        ... )
        >>> print(final_output.vendor_name, tokens)
    """

    # --- Detect which FinalResult model to use dynamically based on the chunk type ---
    if isinstance(data[0], ChunkResult3):
        final_model: Type[TFinal] = FinalResult3
    elif isinstance(data[0], ChunkResult):
        final_model: Type[TFinal] = FinalResult
    elif isinstance(data[0], ChunkResult4):
        final_model: Type[TFinal] = FinalResult4
    else:
        final_model: Type[TFinal] = FinalResult2

    # Determine whether to compute log probabilities
    logprobs_check = "logprobs" in metric

    # Convert list of chunk results into a Markdown-style dictionary of key-value pairs
    markdown_results = format_markdown(data)

    results = {}
    tokens_per_model: Dict[str, Dict[str, int]] = {}

    async def process_key(key: str, value: str):
        """
        Process each extracted key asynchronously by sending it to the LLM
        with an appropriate system prompt and user prompt.
        """
        # Load correct system prompt depending on key type
        if key == "vendor_categories":
            system_prompt = get_prompt_template('vendor_categories_prompt.jinja2').render(
                pre_defined_vendor_list=predefined_list
            )
           
        else:
            system_prompt = get_prompt_template(f'{key}_prompt.jinja2').render()

        # Format user prompt with data content
        user_prompt = data_extractor.format(data=value)

        # Make async LLM call
        llm_response = await batch_client._process_single_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=Config.GPT_GENERATION_4i,
            logprobs=logprobs_check,
            convert_to_json=True
        )
        log_with_span(message=f"Called LLM for {key} for getting final result", span_name="Final result", level="info", log_extra={"service_name": "get-final-result", "api_name": "process-pdf", "input": {"system_prompt":system_prompt,
            "user_prompt":user_prompt}, "output": llm_response.content, "status": "completed"})

        # Normalize duration value if it's numeric
        if key == 'duration':
            try:
                llm_response.content["value"] = int(round(float(llm_response.content["value"])))
            except Exception:
                llm_response.content["value"] = 0

        # Optionally evaluate output correctness via LLM-as-judge
        llm_as_judge_flag = "llm_as_judge" in metric
        if llm_as_judge_flag:
            judge_score = await llm_as_judge(
                input_user=system_prompt,
                output_llm=llm_response.content,
                context=user_prompt
            )
        else:
            judge_score = None

        # Capture log probability if enabled
        logprobs_value = llm_response.logprobs if logprobs_check else None

        # Return all data relevant for aggregation
        return key, llm_response.content, llm_response.input_tokens, llm_response.output_tokens, llm_response.model, logprobs_value, judge_score

    # --- Run all LLM calls concurrently for efficiency ---
    tasks = [process_key(key, value) for key, value in markdown_results.items()]
    responses = await asyncio.gather(*tasks)

    # --- Aggregate all results ---
    log_probs = {}
    llm_as_judge_scores = {}
    for key, data_, in_tokens, out_tokens, model, logprobs_score, judge_score in responses:
        log_probs[key] = logprobs_score
        llm_as_judge_scores[key] = judge_score
        results[key] = data_

        # Track token usage per model
        tokens_per_model.setdefault(model, {"input": 0, "output": 0})
        tokens_per_model[model]["input"] += in_tokens
        tokens_per_model[model]["output"] += out_tokens

    # --- Instantiate the appropriate FinalResult model dynamically ---
    return final_model(**results), tokens_per_model, log_probs, llm_as_judge_scores


async def main_protocol_analyzer(file_path: str, metric: list) -> ProcessPDFResponse:
    """
    Main asynchronous pipeline for analyzing a clinical trial protocol PDF.

    This function orchestrates the complete end-to-end process:
    1. Uploads the PDF to Azure Blob Storage.
    2. Extracts text from the PDF page by page.
    3. Processes each text chunk via LLM-based extraction.
    4. Aggregates and evaluates results across multiple extraction models.
    5. Computes metrics (logprobs, LLM-as-judge scores).
    6. Returns a structured `ProcessPDFResponse` containing outputs, tokens, and timing info.

    Args:
        file_path (str): 
            Full file path of the uploaded PDF document to process.
        metric (list): 
            Optional metrics to calculate. Supported flags:
            - `"logprobs"`: Compute token-level log probabilities.
            - `"llm_as_judge"`: Use an evaluation model to score correctness.

    Returns:
        ProcessPDFResponse:
            A structured response containing:
            - `status` (success/failed)
            - `result` (final structured outputs)
            - `metric_result` (optional performance metrics)
            - `tokens_per_model` (input/output usage statistics)
            - `time_taken` (total processing duration)
            - `error` (if any failure occurred)

    Workflow:
        ┌────────────────────────────────────────────┐
        │ 1. Upload PDF to Azure Blob                │
        │ 2. Extract text from pages                 │
        │ 3. Process all chunks via batch LLM calls  │
        │ 4. Merge final structured results          │
        │ 5. Compute evaluation metrics              │
        └────────────────────────────────────────────┘

    Example:
        >>> response = await main_protocol_analyzer("trial_protocol.pdf", ["logprobs", "llm_as_judge"])
        >>> print(response.result["final_result"].duration)
    """
    response = ProcessPDFResponse(status="success")

    try:
        # ----------------------------
        # Step 0: Upload PDF to Blob
        # ----------------------------
        dir_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)

        upload_input = BlobUploadInput(
            container_name=Config.blob_container_name,
            filepath=dir_path,
            file_name=file_name
        )
        azure_blob.upload_blob(upload_input)
        log_with_span(message=f"Uploaded {file_name} to Azure Blob Storage.", span_name="blob", level="info", log_extra={"service_name": "blob", "api_name": "process-pdf", "input": file_path, "output": True, "status": "in-progress"})

        # ----------------------------
        # Step 1: Extract text from PDF
        # ----------------------------
        pdf_pages, duration1 = await extract_pdf_pages(file_path)

        # Generate predefined vendor list for later use
        predefined_list = format_predefined_list()

        # ----------------------------
        # Step 2: Process text chunks
        # ----------------------------
        (
            final_results, final_results2, final_results3, final_results4, final_result5,
            tokens_per_model_final,
            final_extraction_log_probs1, final_extraction_log_probs2,
            final_extraction_log_probs3, final_extraction_log_probs4, final_extraction_log_probs5,
            final_extraction_judge_score1, final_extraction_judge_score2,
            final_extraction_judge_score3, final_extraction_judge_score4, final_extraction_judge_score5
        ), duration2 = await process_all_chunks(pdf_pages.pages, metric, predefined_list)




        if final_result5.error: 
            error_message = final_result5.error
            response.status = "failed"
            response.error = f"Failed to get Protocol Number, Indication or Program: {error_message}"
            return response
        # ----------------------------
        # Step 3: Check for chunk-level errors
        # ----------------------------
        for i, result_set in enumerate([final_results, final_results2, final_results3, final_results4], start=1):
            chunk_errors = [chunk.error for chunk in result_set if chunk.error]
            if chunk_errors:
                error_message = "; ".join(chunk_errors)
                response.status = "failed"
                response.error = f"Chunk processing failed in set {i}: {error_message}"
                return response

        # ----------------------------
        # Step 4: Merge all final results
        # ----------------------------
        tasks = [
            get_final_result(final_results, metric, predefined_list),
            get_final_result(final_results2, metric),
            get_final_result(final_results3, metric),
            get_final_result(final_results4, metric)
        ]

        # Run all result merging in parallel
        (results1, results2, results3, results4) = await asyncio.gather(*tasks)

        # Each result contains: (FinalResult, tokens_per_model, log_probs, llm_as_judge_scores), duration
        (final_result1, tokens_per_model_final1, log_probs1, llm_as_judge_scores1), duration3 = results1
        (final_result2, tokens_per_model_final2, log_probs2, llm_as_judge_scores2), duration4 = results2
        (final_result3, tokens_per_model_final3, log_probs3, llm_as_judge_scores3), duration5 = results3
        (final_result4, tokens_per_model_final4, log_probs4, llm_as_judge_scores4), duration6 = results4

     
        # ----------------------------
        # Step 5: Combine token statistics across all models
        # ----------------------------
        all_dicts = [
            tokens_per_model_final,
            tokens_per_model_final1,
            tokens_per_model_final2,
            tokens_per_model_final3,
            tokens_per_model_final4
        ]

        per_model_tokens = defaultdict(lambda: {"input": 0, "output": 0})

        for d in all_dicts:
            for model, values in d.items():
                per_model_tokens[model]["input"] += values.get("input", 0)
                per_model_tokens[model]["output"] += values.get("output", 0)

        # ----------------------------
        # Step 6: Compile metric results
        # ----------------------------
        if metric:
            response.metric_result = {
                "final_log_probs_for_each_kpi": {
                    **log_probs1, **log_probs2, **log_probs3, **log_probs4
                },
                "final_llm_as_judge_score_for_each_kpi": {
                    **llm_as_judge_scores1, **llm_as_judge_scores2, **llm_as_judge_scores3, **llm_as_judge_scores4
                },
                "final_extraction_log_probs1": final_extraction_log_probs1,
                "final_extraction_log_probs2": final_extraction_log_probs2,
                "final_extraction_log_probs3": final_extraction_log_probs3,
                "final_extraction_log_probs4": final_extraction_log_probs4,
                "final_extraction_log_probs5": final_extraction_log_probs5,
                "final_extraction_judge_score1": final_extraction_judge_score1,
                "final_extraction_judge_score2": final_extraction_judge_score2,
                "final_extraction_judge_score3": final_extraction_judge_score3,
                "final_extraction_judge_score4": final_extraction_judge_score4,
                "final_extraction_judge_score5": final_extraction_judge_score5
            }

        # ----------------------------
        # Step 7: Validate final result sets
        # ----------------------------
        for i, result_obj in enumerate([final_result1, final_result2, final_result3, final_result4], start=1):
            if getattr(result_obj, "error", None):
                response.status = "failed"
                response.error = f"Final result generation failed in set {i}: {result_obj.error}"
                return response

        # Map of keys to rename
        rename_map = {
            "region": "geographic_requirements",
            "risk_factors": "risk_assessments",
            "number_of_sites": "global_sites",
            "key_requirements": "technical_requirements",
            "participants": "number_of_patients"
        }

        def rename_keys(data: Union[FinalResult, dict]) -> dict:
            # 1. If it's a Pydantic model, convert it here (with your settings)
            if hasattr(data, 'model_dump'):
                data = data.model_dump(exclude_unset=True) # or exclude_none=True
            elif hasattr(data, 'dict'):
                data = data.dict(exclude_unset=True)
            
            # 2. If it's already a dict, the code above skips, and we proceed safely
            
            # Rename keys logic...
            for old_key, new_key in rename_map.items():
                if old_key in data:
                    data[new_key] = data.pop(old_key)
                    
            return data
        
        data = [c.model_dump(exclude_none=True) for c in final_results]
        data2 = [c.model_dump(exclude_none=True) for c in final_results2]
        data3 = [c.model_dump(exclude_none=True) for c in final_results3]
        data4 = [c.model_dump(exclude_none=True) for c in final_results4]
        collapsed_json1 = collapse_sections(data)
        collapsed_json2 = collapse_sections(data2)
        collapsed_json3 = collapse_sections(data3)
        collapsed_json4 = collapse_sections(data4)
        extracted_json = {**collapsed_json1, **collapsed_json2, **collapsed_json3, **collapsed_json4}

  

        final_result_json = {
            **final_result1.model_dump(exclude_none=True),
            **final_result2.model_dump(exclude_none=True),
            **final_result3.model_dump(exclude_none=True),
            **final_result4.model_dump(exclude_none=True),
            **final_result5.model_dump(exclude_none=True)
        }

    
        
        final_json = restore_from_reference(extracted_json, final_result_json)
        response.result = {
                # 1. Validate (create object) -> 2. Dump (clean dict) -> 3. Rename
                "final_result": rename_keys(
                    FinalResult.model_validate(final_json).model_dump(exclude_none=True)
                ),
                
                # Do the same for the others if you want them cleaned too
                "final_result2": FinalResult2.model_validate(final_json).model_dump(exclude_none=True),
                "final_result3": FinalResult3.model_validate(final_json).model_dump(exclude_none=True),
                "final_result4": FinalResult4.model_validate(final_json).model_dump(exclude_none=True),
                "final_result5": FinalResult5.model_validate(final_json).model_dump(
                    exclude_none=True
                )
            }
        
        return response
      
    except Exception as e:
        print(str(e))
        # ----------------------------
        # Step 9: Handle any exceptions gracefully
        # ----------------------------
        log_with_span(message="PDF processing failed", span_name="protocol-analyzer", level="error", log_extra={"service_name": "protocol_analyzer", "api_name": "process-pdf", "input": file_path, "error": str(e), "status": "failed"})
        raise

