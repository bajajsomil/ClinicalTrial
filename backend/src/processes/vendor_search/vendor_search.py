
import asyncio
import traceback
from datetime import datetime
from typing import List, Dict, Any, Tuple
from src.adapters.tavily import AsyncTavilyHelper
from src.utils_helper import timing_decorator
from src.adapters.azure_openai import batch_client
from src.adapters.logger import log_with_span
from src.processes.vendor_search.vendor_queries import query
from src.processes.vendor_search.prompts.user_prompt import *
from src.processes.vendor_search.models import VendorInfo, AnalysisResult
from src.processes.vendor_search.prompts.system import get_prompt_template
import json

def vendor_query(vendor_info: VendorInfo) -> Dict[str, List[str]]:
    """
    Generate structured search queries for a given vendor.

    This function populates pre-defined query templates with vendor metadata.

    Args:
        vendor_info (VendorInfo): Dataclass or Pydantic model containing vendor metadata.

    Returns:
        Dict[str, List[str]]: A mapping where:
            - Key: Section name (e.g., "capabilities", "locations").
            - Value: List of formatted search query strings.

    Raises:
        ValueError: If query generation fails due to template formatting or missing vendor fields.
    """
    try:
        # Build queries by formatting predefined search templates with vendor metadata
        queries: Dict[str, List[str]] = {
            section: [template.format(**vendor_info.dict()) for template in templates]
            for section, templates in query.search_queries.items()
        }
        return queries

    except KeyError as e:
        raise ValueError(f"Missing field in vendor_info while generating queries: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to generate vendor queries: {e}") from e
    
async def analyze_with_openai(
    vendor_info: VendorInfo,
    question_category: str,
    query: str,
    search_result: List[Dict[str, Any]],
    answer: str,
) -> Tuple[Dict[str, Any], int, int, str]:
    """
    Analyze search results using OpenAI/GPT.

    The function builds a rich contextual prompt from search results and vendor metadata,
    sends it to the model, and returns the structured analysis response.

    Args:
        vendor_info (VendorInfo): Vendor metadata.
        question_category (str): Category of the query being analyzed.
        query (str): The actual search query executed.
        search_result (List[Dict[str, Any]]): List of search result entries.
        answer (str): Initial search answer or summary.

    Returns:
        Tuple[Dict[str, Any], int, int, str]:
            - Parsed GPT response content
            - Input token count
            - Output token count
            - Model name used

    Raises:
        ValueError: If LLM response or parsing fails.
    """
    try:
        # Build text context from search results
        content_blocks: List[str] = [
            (
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL: {r.get('url', 'N/A')}\n"
                f"Content: {r.get('content', 'N/A')}\n"
                f"Published Date: {r.get('published_date', 'N/A')}"
            )
            for r in search_result
        ]

        search_context = "\n\n".join(content_blocks)

        # Prepare system and user prompts
        system_prompt = get_prompt_template("vendor_external_info_prompt.jinja2").render()
        user_prompt = vendor_search.format(
            vendor_name=vendor_info.vendor_name,
            vendor_category=vendor_info.vendor_category,
            question_category=question_category,
            query=query,
            answer=answer,
            search_context=search_context,
        )

        # Call OpenAI asynchronously
        llm_response = await batch_client._process_single_request(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            convert_to_json=True
        )

        log_with_span(f"Called LLM for each tavily response and query", "AnalyzeWithOpenAI", "info", log_extra={"service_name": "vendor_external_info", "api_name": "vendor_search","input": {"system_prompt": system_prompt, "user_prompt": vendor_search.format(
            vendor_name=vendor_info.vendor_name,
            vendor_category=vendor_info.vendor_category,
            question_category=question_category,
            query=query,
            answer=answer,
            search_context=search_context,
        )}
        ,"output": llm_response.content, "status": "in-progress"})

        return (
            llm_response.content,
            llm_response.input_tokens,
            llm_response.output_tokens,
            llm_response.model,
        )

    except Exception as e:
        log_with_span(f"[{__name__}] OpenAI analysis failed for query '{query}': {str(e)}", "AnalyzeWithOpenAI", "error", log_extra={"query": query, "error": str(e)})
        return {}, 0, 0, ""
    
async def vendor_info_gene(
    output: Dict[str, Any],
    vendor_info: VendorInfo
) -> AnalysisResult:
    """
    Generate structured vendor information using GPT responses and track token usage per model.

    This function sends three parallel LLM requests for:
      - Vendor Capabilities
      - Positive News
      - Negative News

    The responses are combined into a structured `AnalysisResult` object.

    Args:
        output (Dict[str, Any]): Intermediate GPT or search results (capabilities, news, etc.).
        vendor_info (VendorInfo): Metadata describing the vendor (name, category, date range, etc.).

    Returns:
        AnalysisResult: Consolidated vendor information with model-level token usage.

    Raises:
        ValueError: If one or more GPT calls fail or responses are invalid.
    """
    try:
        # Prepare user prompts
        vendor_capability_user_prompt = capability_user_prompt.format(
            vendor_name=vendor_info.vendor_name,
            input_data=output.get("capabilities", {})
        )

        vendor_positive_news_user_prompt = positive_news_user_prompt.format(
            vendor_name=vendor_info.vendor_name,
            input_data=output.get("positive_news", {}),
            start=vendor_info.start_year,
            end=vendor_info.end_year,
        )

        vendor_negative_news_user_prompt = negative_news_user_prompt.format(
            vendor_name=vendor_info.vendor_name,
            input_data=output.get("negative_news", {}),
            start=vendor_info.start_year,
            end=vendor_info.end_year,
        )

        # Prepare system prompts
        capability_system_prompt = get_prompt_template("vendor_capabilities_prompt.jinja2").render()
        positive_news_system_prompt = get_prompt_template("vendor_positive_news_prompt.jinja2").render()
        negative_news_system_prompt = get_prompt_template("vendor_negative_news_prompt.jinja2").render()

        # Batch async call for all three
        (
            capability_result,
            positive_result,
            negative_result
        ) = await batch_client.get_batch_responses(
            [
                (capability_system_prompt, vendor_capability_user_prompt),
                (positive_news_system_prompt, vendor_positive_news_user_prompt),
                (negative_news_system_prompt, vendor_negative_news_user_prompt),
            ],
            json_mode=True,
            convert_to_json=True
        )

        # Aggregate token usage by model
        token_usage: Dict[str, Dict[str, int]] = {}
        for result in (capability_result, positive_result, negative_result):
            if not hasattr(result, "model"):
                continue
            model = result.model
            token_usage.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
            token_usage[model]["input_tokens"] += getattr(result, "input_tokens", 0)
            token_usage[model]["output_tokens"] += getattr(result, "output_tokens", 0)

        # Construct final structured result
        analysis = AnalysisResult(
            capabilities=capability_result.content if hasattr(capability_result, "content") else {},
            positive_news=positive_result.content if hasattr(positive_result, "content") else {},
            negative_news=negative_result.content if hasattr(negative_result, "content") else {},
            token_usage_per_model=token_usage,
        )

        log_with_span(f"Vendor info generated successfully for {vendor_info.vendor_name} using LLM", "VendorInfoGene", "info", log_extra={"service_name": "category-wise-LLM","api_name": "vendor_search","input": {"capability": {"system_prompt": capability_system_prompt, "user_prompt": vendor_capability_user_prompt},
                "positive_news": {"system_prompt": positive_news_system_prompt, "user_prompt": vendor_positive_news_user_prompt},
                "negative_news": {"system_prompt": negative_news_system_prompt, "user_prompt": vendor_negative_news_user_prompt}},
            "output": {"capability": capability_result.content, "positive_news": positive_result.content, "negative_news": negative_result.content}, "status": "completed"})

        return analysis

    except Exception as e:
        log_with_span(f"[{__name__}] Vendor info generation failed: {str(e)}", "VendorInfoGene", "error", log_extra={"error": str(e)})
        raise

@timing_decorator
async def main_vendor_search(vendor_name: str, vendor_category: str, tavily_api_key: str = None) -> Dict[str, Any]:
    """
    Main service function to process vendor information and return structured analysis.

    Steps:
        1. Generate queries from vendor metadata.
        2. Perform concurrent web searches per query.
        3. Analyze retrieved data using GPT (via batch_client).
        4. Consolidate structured vendor insights (capabilities, positive/negative news).
        5. Aggregate token usage across all models.

    Args:
        vendor_name (str): Vendor name.
        vendor_category (str): Vendor category.

    Returns:
        Dict[str, Any]: Response structure with success flag, structured data, and model token usage.
    """
    try:
        Tavily_client = AsyncTavilyHelper()
        vendor_info = VendorInfo(
            vendor_name=vendor_name,
            vendor_category=vendor_category,
            start_year=datetime.now().year - 1,
            end_year=datetime.now().year,
        )

        # Step 1: Generate queries
        queries = vendor_query(vendor_info)
    

        # Step 2: Search concurrently
        search_results: Dict[str, Dict[str, Any]] = {}
        for section, query_list in queries.items():
            # Launch all queries in this section concurrently
            tasks = [Tavily_client.get_response(query, section, api_key=tavily_api_key) for query in query_list]
            search_responses = await asyncio.gather(*tasks)

            # Store results
            search_results[section] = {
                query: {
                    "search_result": search_result[1],
                    "search_answer": answer[1]
                }
                for query, (search_result, answer,latency_seconds) in zip(query_list, search_responses)
            }
            print("RESPONSES", search_responses)

        log_with_span(f"Searched all queries in tavily", "MainVendorSearch", "info", log_extra={"service_name": "tavily_api", "api_name": "vendor_search","input": queries, "output": search_results, "status": "completed"})

        # Step 3: Analyze results with GPT concurrently and accumulate tokens
        que_ans_result: Dict[str, Dict[str, Any]] = {}
        token_usage: Dict[str, Dict[str, int]] = {}

        for category, section_queries in search_results.items():
            queries_list = list(section_queries.keys())
            tasks = [
                analyze_with_openai(
                    vendor_info, category, query, res["search_result"], res["search_answer"]
                )
                for query, res in section_queries.items()
            ]

            responses = await asyncio.gather(*tasks)
            print("OPENAI RESPONSES", responses)

            que_ans_result[category] = {}
            for query, response in zip(queries_list, responses):
                # response = (decoded_data, input_tokens, output_tokens, model)
                if len(response) == 4:
                    decoded_data, input_tokens, output_tokens, model = response
                else:  # fallback if something failed
                    decoded_data, input_tokens, output_tokens, model = {}, 0, 0, "unknown"

                que_ans_result[category][query] = decoded_data

                # Accumulate tokens per model
                if model not in token_usage:
                    token_usage[model] = {"input_tokens": 0, "output_tokens": 0}
                token_usage[model]["input_tokens"] += input_tokens
                token_usage[model]["output_tokens"] += output_tokens

        # Step 4: Generate final structured vendor info
        output = await vendor_info_gene(que_ans_result, vendor_info)
        print("INFO GENE OUTPUT", output)

        # Merge GPT token usage from vendor_info_gene with the tokens from analyze_with_openai
        if output.token_usage_per_model:
            for model, tokens in output.token_usage_per_model.items():
                if model not in token_usage:
                    token_usage[model] = tokens
                else:
                    token_usage[model]["input_tokens"] += tokens.get("input_tokens", 0)
                    token_usage[model]["output_tokens"] += tokens.get("output_tokens", 0)
        with open("token_usage.json", "w") as f:
            json.dump(token_usage, f, indent=4)
        # Include aggregated token usa ge in final response
        return {"success": True, "response": output.dict(), "token_usage_per_model": token_usage}

    except Exception as e:
        error = traceback.format_exc()
        log_with_span(f"[{__name__}] ERROR: {error}", "MainVendorSearch", "error", log_extra={"service_name": "vendor_search", "api_name": "vendor_search", "input": {"vendor_name": vendor_name, "vendor_category": vendor_category}, "status": "failed", "error": error})
        raise
