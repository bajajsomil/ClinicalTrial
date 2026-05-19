import time
from traceback import format_exc
from tavily import AsyncTavilyClient
from tavily.errors import ForbiddenError
from config.config import Config
from src.processes.vendor_search.models import TavilyResponseModel
from src.adapters.logger import log_with_span  # replace logger import

class AsyncTavilyHelper:

    def __init__(self):
        self.tavily_api_key = Config.TAVILY_API_KEY
        self.tavily_client = AsyncTavilyClient(api_key=self.tavily_api_key)
        log_with_span(
            message="Tavily client initialized",
            level="info",
            span_name="Tavily Initialization",
            log_extra={
                "service_name": "tavily",
                "api_name": "vendor_search",
                "input": None,
                "output": "Tavily client ready",
                "status": "success",
                "error": None
            }
        )

    async def get_response(self, query: str, question_category: str, api_key: str = None) -> TavilyResponseModel:
        """
        Execute a Tavily search query and return a structured response.
        Handles category-specific search parameters, response parsing, and latency tracking.

        Args:
            query (str): The search query string.
            question_category (str): Category of the query (e.g., "capabilities", "positive_news", "negative_news").

        Returns:
            TavilyResponseModel: Structured search response including results, answer, and latency.
        """
        span_name = "Tavily Query Execution"
        try:
            start = time.time()

            client = AsyncTavilyClient(api_key=api_key) if api_key else self.tavily_client

            # Handle capabilities query
            if question_category == "capabilities":
                response = await client.search(
                    query=query,
                    include_answer="advanced",
                    search_depth="advanced",
                    max_results=5
                )

            # Handle news queries
            elif question_category in ["positive_news", "negative_news"]:
                response = await client.search(
                    query=query,
                    include_answer="advanced",
                    topic="news",
                    time_range="year",
                    search_depth="advanced",
                    max_results=5
                )

            end = time.time()
            latency = end - start

            # ---------------------------
            # SUCCESS LOG
            # ---------------------------
            log_with_span(
                message="Tavily query executed successfully",
                level="info",
                span_name=span_name,
                log_extra={
                    "service_name": "tavily",
                    "api_name": "vendor_search",
                    "input": {"query": query, "question_category": question_category},
                    "output": {
                        "results": response.get("results", []),
                        "answer": response.get("answer", "")
                    },
                    "status": "success",
                    "error": None
                }
            )

            return TavilyResponseModel(
                search_result=response.get("results", []),
                answer=response.get("answer", ""),
                latency_seconds=latency
            )

        except ForbiddenError as e:
            # ---------------------------
            # PLAN LIMIT LOG
            # ---------------------------
            log_with_span(
                message="Tavily usage limit reached",
                level="error",
                span_name=span_name,
                log_extra={
                    "service_name": "tavily",
                    "api_name": "vendor_search",
                    "input": {"query": query, "question_category": question_category},
                    "output": None,
                    "status": "failed",
                    "error": str(e)
                }
            )
            raise Exception("Tavily API usage limit exceeded. Please upgrade your plan or contact support.")

        except Exception as e:
            # Soft fail for all OTHER errors → return EMPTY RESULT
            error_trace = format_exc()

            log_with_span(
                message="Tavily API request failed (soft fail, returned empty)",
                level="error",
                span_name=span_name,
                log_extra={
                    "service_name": "tavily",
                    "api_name": "vendor_search",
                    "input": {"query": query, "question_category": question_category},
                    "output": None,
                    "status": "soft-failed",
                    "error": error_trace
                }
            )

            # Return an empty response instead of raising
            return TavilyResponseModel(
                search_result=[],
                answer="",
                latency_seconds=0.0
            )


