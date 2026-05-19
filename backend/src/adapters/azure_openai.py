import asyncio
import time
import random
import math
from typing import List, Tuple
from openai import AsyncAzureOpenAI
import json
from config.config import Config
from src.models import DecodeJsonResult, AzureResponseModel
from src.adapters.logger import log_with_span


class AzureOpenAIHelper:
    """
    Helper class for batch processing multiple Azure OpenAI requests concurrently.
    Supports JSON mode, token usage tracking, confidence scores, and detailed metrics.
    """

    def __init__(self):
        self.azure_endpoint = Config.AZURE_OPENAI_ENDPOINT
        self.api_key = Config.AZURE_OPENAI_KEY
        self.api_version = Config.AZURE_OPENAI_VERSION
        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

        log_with_span(
            message="Initialized AzureOpenAIHelper",
            span_name="AzureOpenAI",
            level="info",
            log_extra={
                "service_name": "Azure OpenAI",
                "input": None,
                "output": f"Endpoint: {self.azure_endpoint}",
                "status": "Started",
                "error": None
            }
        )

    @staticmethod
    def _decode_json(text: str) -> DecodeJsonResult:
        try:
            decoder = json.JSONDecoder()
            pos = 0
            json_objects = []

            while pos < len(text):
                try:
                    obj, idx = decoder.raw_decode(text, pos)
                    json_objects.append(obj)

                    log_with_span(
                        message="JSON object decoded",
                        span_name="decode_json",
                        level="debug",
                        log_extra={
                            "service_name": "Azure OpenAI",
                            "input": text,
                            "output": str(obj),
                            "status": "Started",
                            "error": None,
                        }
                    )

                    pos = idx
                    while pos < len(text) and text[pos].isspace():
                        pos += 1

                except json.JSONDecodeError as e:
                    log_with_span(
                        message="JSON decoding warning",
                        span_name="decode_json",
                        level="warning",
                        log_extra={
                            "service_name": "Azure OpenAI",
                            "input": text,
                            "output": None,
                            "status": "Failed",
                            "error": str(e),
                        }
                    )
                    pos += 1
                except Exception as e:
                    log_with_span(
                        message="Unexpected JSON decode error",
                        span_name="decode_json",
                        level="error",
                        log_extra={
                            "service_name": "Azure OpenAI",
                            "input": text,
                            "output": None,
                            "status": "failed",
                            "error": str(e),
                        }
                    )
                    pos += 1

            if json_objects:
                # logger.info("Successfully decoded JSON object(s)")
                for i in json_objects:
                    if isinstance(i,dict):
                        print("json decode result: ", i)
                        return DecodeJsonResult(data=i)
                return DecodeJsonResult(error= "No JSON decoded")
                # return DecodeJsonResult(data=json_objects[0])
            else:
                # logger.error("No JSON object could be decoded from the text")
                return DecodeJsonResult(error="No JSON decoded")

        except Exception as e:
            log_with_span(
                message="Fatal JSON decode error",
                span_name="decode_json",
                level="critical",
                log_extra={
                    "service_name": "Azure OpenAI",
                    "input": text,
                    "output": None,
                    "status": "failed",
                    "error": str(e),
                }
            )
            return DecodeJsonResult(error=str(e))

    @staticmethod
    def _calculate_confidence_score(choice) -> float:
        if hasattr(choice, "logprobs") and choice.logprobs and choice.logprobs.content:
            values = [t.logprob for t in choice.logprobs.content if t.logprob is not None]
            if values:
                return math.exp(sum(values) / len(values))
        return 0.0

    async def _process_single_request(
            self,
            system_prompt: str,
            user_prompt: str,
            json_mode: bool = False,
            convert_to_json: bool = False,
            model: str = Config.GPT_GENERATION_4O_MINI_MODEL,
            logprobs: bool = False,
            retries: int = 2,
            request_index: int = 0,
            timeout_seconds: int = 120
        ) -> AzureResponseModel:

        TIMEOUT_SECONDS = timeout_seconds  # 1 minute timeout

        for attempt in range(1, retries + 1):
            try:
                log_with_span(
                    message=f"Sending request attempt {attempt}",
                    span_name="AzureOpenAI_Request",
                    level="info",
                    log_extra={
                        "service_name": "Azure OpenAI",
                        "input": user_prompt,
                        "output": None,
                        "status": "sending",
                        "error": None
                    }
                )

                start = time.time()

                # ----- APPLY TIMEOUT -----
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        temperature=0,
                        seed=123,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        top_p=0.9,
                        logprobs=logprobs,
                        response_format={"type": "json_object"} if json_mode else None,
                    ),
                    timeout=TIMEOUT_SECONDS
                )
                
                end = time.time()
                latency = end - start

                choice = response.choices[0]
                content = choice.message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                confidence = self._calculate_confidence_score(choice) if logprobs else 0.0

                log_with_span(
                    message="Azure OpenAI response received",
                    span_name="AzureOpenAI_Request",
                    level="info",
                    log_extra={
                        "service_name": "Azure OpenAI",
                        "input": user_prompt,
                        "output": content,
                        "status": "success",
                        "error": None
                    }
                )

                decoded_json = {}
                if convert_to_json:
                    dec = self._decode_json(content)
                    if dec.error:
                        log_with_span(
                            message="JSON decode failed",
                            span_name="AzureOpenAI_Request",
                            level="warning",
                            log_extra={
                                "service_name": "Azure OpenAI",
                                "input": content,
                                "output": {},
                                "status": "decode_failed",
                                "error": dec.error
                            }
                        )
                    else:
                        decoded_json = dec.data
                        if not isinstance(decoded_json, dict):
                            print("NOT JSON")
                            decoded_json = {}


                return AzureResponseModel(
                    content=decoded_json if convert_to_json else content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=model,
                    latency_seconds=latency,
                    logprobs=confidence
                )

            except asyncio.TimeoutError:
                # ----- TIMEOUT HANDLING -----
                log_with_span(
                    message=f"Azure OpenAI request timed out ({timeout_seconds}s)",
                    span_name="AzureOpenAI_Request",
                    level="error",
                    log_extra={
                        "service_name": "Azure OpenAI",
                        "input": user_prompt,
                        "output": None,
                        "status": "timeout",
                        "error": "Request exceeded 60 seconds"
                    }
                )

                #  retries due to timeout
                if attempt < retries:
                    backoff = (2 ** attempt) + random.random()
                    await asyncio.sleep(backoff)

            except Exception as ex:
                print(str(ex))
                # ----- GENERAL ERROR -----
                log_with_span(
                    message="Azure OpenAI request failed",
                    span_name="AzureOpenAI_Request",
                    level="error",
                    log_extra={
                        "service_name": "Azure OpenAI",
                        "input": user_prompt,
                        "output": None,
                        "status": "error",
                        "error": str(ex)
                    }
                )

                if attempt < retries:
                    backoff = (2 ** attempt) + random.random()
                    await asyncio.sleep(backoff)

        # ----- ALL RETRIES EXHAUSTED -----
        log_with_span(
            message="All retries exhausted",
            span_name="AzureOpenAI_Request",
            level="error",
            log_extra={
                "service_name": "Azure OpenAI",
                "input": user_prompt,
                "output": None,
                "status": "failed",
                "error": f"Failed after {retries} attempts"
            }
        )

        return AzureResponseModel(
            content={} if (json_mode or convert_to_json) else "",
            input_tokens=0,
            output_tokens=0,
            model=model,
            latency_seconds=0.0,
            logprobs=0.0
        )


    async def get_batch_responses(
        self,
        prompts: List[Tuple[str, str]],
        json_mode: bool = False,
        convert_to_json: bool = False,
        model: str = Config.GPT_GENERATION_4O_MINI_MODEL,
        logprobs: bool = False,
        retries: int = 2,
        timeout_seconds: int = 120
    ) -> List[AzureResponseModel]:

        log_with_span(
            message="Batch processing started",
            span_name="AzureOpenAI_Batch",
            level="info",
            log_extra={
                "service_name": "Azure OpenAI",
                "input": f"Total prompts: {len(prompts)}",
                "output": None,
                "status": "started",
                "error": None
            }
        )

        batch_start = time.time()

        tasks = [
            self._process_single_request(
                system_prompt=sys_p,
                user_prompt=user_p,
                json_mode=json_mode,
                convert_to_json=convert_to_json,
                model=model,
                logprobs=logprobs,
                retries=retries,
                request_index=i,
                timeout_seconds = timeout_seconds
            )
            for i, (sys_p, user_p) in enumerate(prompts)
        ]

        responses = await asyncio.gather(*tasks)

        batch_end = time.time()

        log_with_span(
            message="Batch processing completed",
            span_name="AzureOpenAI_Batch",
            level="info",
            log_extra={
                "service_name": "Azure OpenAI",
                "input": f"Total prompts: {len(prompts)}",
                "output": f"Batch latency: {batch_end - batch_start:.2f}s",
                "status": "completed",
                "error": None
            }
        )

        return responses


batch_client = AzureOpenAIHelper()
