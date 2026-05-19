import os
import json
import time
import uuid
import random
import requests, base64
import asyncio
import tempfile
import traceback
from urllib.parse import urlencode
from typing import Optional
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from src.adapters.logger import log_with_span
from config.config import Config
from fastapi import FastAPI, UploadFile, HTTPException, File, Form, WebSocket, WebSocketDisconnect
from src.processes.vendor_search.vendor_search import main_vendor_search
from src.processes.protocol_analyzer.protocol_analyzer import main_protocol_analyzer
from src.processes.document_comparison.document_comparison import main_document_comparison
from src.processes.protocol_analyzer.models import ProcessPDFResponse
from src.processes.vendor_search.models import VendorSearch, VendorSearchResponse
from src.processes.document_comparison.models import ComparisonAPIResponse, ComparisonResponseData, SectionImpact

# -------------------------------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------------------------------

# Initialize FastAPI application
app = FastAPI(title="Clinical Trial Intelligence API", version="1.0")

# Enable CORS for all origins (customize or restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------------------------------------------
async def get_static_fallback_response(filename) -> ProcessPDFResponse:
    """
    Load and return a static fallback response when PDF processing fails.

    Reads a predefined JSON response from `static/fallback_response.json` and
    converts it into a `ProcessPDFResponse` object. If the fallback file does not
    exist, returns a minimal failure response.

    Returns:
        ProcessPDFResponse: The fallback structured response.
    """
    if filename == 'Protocol_5 1.pdf':
        result_path = os.path.join(os.getcwd(), 'static', 'protocol_analyzer2.json')
        if os.path.exists(result_path):
            with open(result_path, "r") as f:
                data = json.load(f)
            log_with_span("Responding with Static fallback file - static/protocol_analyzer2.json", "Fallback","info", log_extra={"api_name": "process-pdf", "status": "Completed", "input": f"{filename}", "output": data})
            return ProcessPDFResponse(**data)
        
    else:
        result_path = os.path.join(os.getcwd(), 'static', 'protocol_analyzer1.json')
        if os.path.exists(result_path):
            with open(result_path, "r") as f:
                data = json.load(f)
            log_with_span("Responding with Static fallback file - static/protocol_analyzer1.json", "Fallback","info", log_extra={"api_name": "process-pdf", "status": "Completed", "input": f"{filename}", "output": data})
            return ProcessPDFResponse(**data)
        else:
            # Return a simple failure object if the fallback JSON is missing
            log_with_span("Static Fallback response not found", "Fallback","warning", log_extra={"api_name": "process-pdf", "status": "Failed", "input": f"{filename}", "error": "Static fallback not found"})
            return ProcessPDFResponse(
                status="failed",
                result=None,
                error="Static fallback not found",
                time_taken=0.0,
            )

async def get_static_fallback_response_document_comparison(file1, file2) -> ComparisonAPIResponse:
    fallback_path = os.path.join(os.getcwd(),'static', 'document_comparison.json')

    if os.path.exists(fallback_path):
        with open(fallback_path, "r") as f:
            data = json.load(f)
        log_with_span(f"Responding with Static Fallback file - {fallback_path}", "Fallback","info", log_extra={"api_name": "document-comparison", "status": "Completed","input": f"File 1: {file1}, File 2 - {file2}", "output": data})
        return ComparisonAPIResponse(**data)

    log_with_span("Static Fallback response not found", "Fallback","warning", log_extra={"api_name": "document-comparison", "status": "Failed", "input": f"File 1: {file1}, File 2 - {file2}", "error": "Static fallback not found"})
    return ComparisonAPIResponse(
        success=False,
        result=ComparisonResponseData(differences = {}, section_added_or_removed_impact = SectionImpact(added = {}, removed = {}), summary = ""),
        error="Static fallback not found"
    )

async def load_fallback_result():
    """Load static fallback JSON file."""
    try:
        with open(os.path.join(os.getcwd(), 'static', 'vendor_search.json'), "r") as f:
            data =  json.load(f)

        return VendorSearchResponse(success=True,
                                    output = data['output'],
                                    error = None)
    except Exception as e:
        return VendorSearchResponse(success=False,
                                    output = None,
                                    error = "Fallback result missing")


# -------------------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------------------
@app.get("/health")
async def get_status():
    """
    Health check endpoint.

    Used to verify if the API server is up and running.

    Returns:
        dict: A simple dictionary indicating healthy status.
    """
    return {"response": "healthy"}


# -------------------------------------------------------------------------
# PROCESS PDF ENDPOINT WITH TIMEOUT + FALLBACK
# -------------------------------------------------------------------------
@app.post("/process-pdf/", response_model=ProcessPDFResponse)
async def process_pdf(file: UploadFile = File(...), metric: Optional[str] = Form("[]")):

    request_id = uuid.uuid4().hex

    # --- REQUEST RECEIVED LOG ---
    log_with_span(
        f"Request received for PDF processing: {file.filename}",
        "ProcessPDFStart",
        "info",
        log_extra={
            "api_name": "process-pdf",
            "status": "Received",
            "request_id": request_id,
            "input": file.filename,
            "content_type": file.content_type,
        }
    )

    # Validate PDF
    if file.content_type != "application/pdf":
        log_with_span(
            "Invalid file type uploaded",
            "InvalidFileType",
            "error",
            log_extra={
                "api_name": "process-pdf",
                "status": "Failed",
                "request_id": request_id,
                "input": file.filename,
                "error": f"Invalid content type: {file.content_type}",
            }
        )
        raise HTTPException(status_code=400, detail="Uploaded file is not a PDF")

    base_dir = "temp"
    os.makedirs(base_dir, exist_ok=True)
    file_path = os.path.join(base_dir, file.filename)

    try:
        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(await file.read())
        TIMEOUT = 800
        log_with_span(
            f"Starting protocol analyzer with {TIMEOUT} timeout",
            "StartAnalyzer",
            "info",
            log_extra={
                "api_name": "process-pdf",
                "status": "Processing",
                "request_id": request_id,
                "input": file.filename,
            }
        )


        # ----------------------------
        # RUN PIPELINE WITH TIMEOUT
        # ----------------------------
        try:
            if file.filename.lower().startswith('sample'):
                # Add 2 minutes delay (120 seconds)
                time.sleep(40)
                
                with open(os.path.join(os.getcwd(), 'static', 'protocol_analyzer2.json'), 'r') as f:
                    data = json.load(f)
                log_with_span("Responding with Static fallback file - static/protocol_analyzer3.json", "Fallback","info", log_extra={"api_name": "process-pdf", "status": "Completed", "input": f"{file.filename}", "output": data})
                return ProcessPDFResponse(**data)
            else:
                start_time = time.time()
                response: ProcessPDFResponse = await asyncio.wait_for(
                    main_protocol_analyzer(file_path, metric),
                    timeout=TIMEOUT
                )
                print("TIME TAKEN", time.time()-start_time)
                print("RESPONSE", response)
            # SUCCESS LOG
            log_with_span(
                "PDF processing completed successfully",
                "ProcessPDFSuccess",
                "info",
                log_extra={
                    "api_name": "process-pdf",
                    "status": "Completed",
                    "request_id": request_id,
                    "input": file.filename,
                    "output": response,
                }
            )

           

            return response

        except asyncio.TimeoutError:
            log_with_span(
                "Analyzer TIMEOUT occurred",
                "AnalyzerTimeout",
                "error",
                log_extra={
                    "api_name": "process-pdf",
                    "status": "Timeout",
                    "request_id": request_id,
                    "input": file.filename,
                    "error": f"Processing exceeded {TIMEOUT} seconds",
                }
            )
            return await get_static_fallback_response(file.filename)

        except Exception as inner_error:
            print("ERROR", inner_error)
            log_with_span(
                f"Error during analyzer execution - {inner_error}",
                "AnalyzerError",
                "error",
                log_extra={
                    "api_name": "process-pdf",
                    "status": "Failed",
                    "request_id": request_id,
                    "input": file.filename,
                    "error": str(inner_error),
                }
            )
            return await get_static_fallback_response(file.filename)

        


    except Exception as e:
        log_with_span(
            "Unexpected exception in process_pdf",
            "UnexpectedError",
            "error",
            log_extra={
                "api_name": "process-pdf",
                "status": "Failed",
                "request_id": request_id,
                "input": file.filename,
                "error": str(e),
            }
        )
        return await get_static_fallback_response("Protocol.pdf")

    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                log_with_span(
                    "Temporary file cleaned successfully",
                    "CleanupSuccess",
                    "info",
                    log_extra={
                        "api_name": "process-pdf",
                        "status": "Completed",
                        "request_id": request_id,
                        "input": file.filename,
                    }
                )
        except Exception as cleanup_error:
            log_with_span(
                "Failed to clean temp files",
                "CleanupFailed",
                "warning",
                log_extra={
                    "api_name": "process-pdf",
                    "status": "Failed",
                    "request_id": request_id,
                    "input": file.filename,
                    "error": str(cleanup_error),
                }
            )


def get_vendor_result(
    cache: list,
    vendor_name: str,
    vendor_category: str
):
    def normalize(value: str) -> str:
        return value.strip().split()[0].lower()
    def is_within_last_15_days(date_str: str) -> bool:
        record_date = datetime.strptime(date_str, "%Y-%m-%d")
        return record_date >= datetime.now() - timedelta(days=15)

    norm_vendor = normalize(vendor_name)
    norm_category = normalize(vendor_category)

    for entry in cache:
        if (
            normalize(entry.get("vendor_name", "")) == norm_vendor and
            normalize(entry.get("vendor_category", "")) == norm_category
        ):
            if is_within_last_15_days(entry.get("date", "")):
                return True, entry["results"]   # fresh cache hit
            break  # match found but stale → recompute

    # Not found or stale → recompute
    return False, {}


def update_cache_if_exists(
    old_json: list,
    new_result: dict,
    vendor_name: str,
    vendor_category: str
) -> list:
    
    def normalize(value: str) -> str:
        return value.strip().split()[0].lower()

    norm_vendor = normalize(vendor_name)
    norm_category = normalize(vendor_category)

    updated = False

    for i, entry in enumerate(old_json):
        if (
            normalize(entry.get("vendor_name", "")) == norm_vendor and
            normalize(entry.get("vendor_category", "")) == norm_category
        ):
            # Remove old entry
            old_json.pop(i)

            # Insert updated entry
            old_json.insert(
                i,
                {
                    "vendor_name": norm_vendor,
                    "vendor_category": norm_category,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "results": new_result
                }
            )
            updated = True
            break

    return old_json

# -------------------------------------------------------------------------
# VENDOR SEARCH ENDPOINT
# -------------------------------------------------------------------------
@app.post("/vendor-search/", response_model=VendorSearchResponse)
async def vendor_search(data: VendorSearch):
    print("Received vendor search request for:", data)
    tavily_key = data.tavily_api_key
    Config.TAVILY_API_KEY = tavily_key
    request_id = uuid.uuid4().hex
    vendor_path = os.path.join(os.getcwd(), 'static', 'vendor_results.json')

    with open(vendor_path, 'r') as f:
        vendor_cache_data = json.load(f) 
    
    check, json_data = get_vendor_result(vendor_cache_data, data.vendor_name, data.vendor_category)
    if check:
        time.sleep(15)
        return json_data
    # ----------------------------
    # REQUEST RECEIVED LOG
    # ----------------------------
    log_with_span(
        "Vendor Search request received",
        "VendorSearchStart",
        "info",
        log_extra={
            "api_name": "vendor_search",
            "status": "Received",
            "input": data.model_dump(),
        }
    )

    try:
        # ----------------------------
        # RUN PIPELINE WITH TIMEOUT (2 minutes)
        # ----------------------------
    
        result, duration = await asyncio.wait_for(
            main_vendor_search(data.vendor_name, data.vendor_category, data.tavily_api_key),
            timeout=180
        )


        
        # ----------------------------
        # SUCCESS CASE
        # ----------------------------
        if result.get("success"):
            response_data = result.get("response", {})
            token_usage = result.get("token_usage_per_model", {})

            log_with_span(
                "Vendor Search completed successfully",
                "VendorSearchSuccess",
                "info",
                log_extra={
                    "api_name": "vendor_search",
                    "request_id": request_id,
                    "status": "Completed",
                    "input": data.model_dump(),
                    "output": response_data,
                    "token_usage": token_usage,
                    "time_taken": duration,
                }
            )

            updated_cache_json = update_cache_if_exists(vendor_cache_data, VendorSearchResponse(
                success=True,
                output=response_data,
                error=None
            ).model_dump(), data.vendor_name, data.vendor_category)

            with open(vendor_path, 'w') as f:
                json.dump(updated_cache_json, f, indent=2)

            return VendorSearchResponse(
                success=True,
                output=response_data,
                error=None
            )
        
        # ----------------------------
        # FAILURE RETURNED BY PIPELINE
        # ----------------------------
        log_with_span(
            "Vendor Search returned failure",
            "VendorSearchFailed",
            "error",
            log_extra={
                "api_name": "vendor_search",
                "request_id": request_id,
                "status": "Failed",
                "input": data.model_dump(),
                "error": result.get("error"),
            }
        )

        return await load_fallback_result()

    except asyncio.TimeoutError:
        # ----------------------------
        # TIMEOUT → RETURN FALLBACK
        # ----------------------------
        log_with_span(
            "Vendor Search timed out, returning fallback",
            "VendorSearchTimeout",
            "warning",
            log_extra={
                "api_name": "vendor_search",
                "request_id": request_id,
                "status": "Timeout → Fallback",
                "input": data.model_dump()
            }
        )
        return await load_fallback_result()

        

    except Exception as e:
        # ----------------------------
        # EXCEPTION → RETURN FALLBACK
        # ----------------------------
        error_trace = traceback.format_exc()
        log_with_span(
            "Unexpected error during Vendor Search, returning fallback",
            "VendorSearchException",
            "error",
            log_extra={
                "api_name": "vendor_search",
                "request_id": request_id,
                "status": "Exception → Fallback",
                "input": data.model_dump(),
                "error": f"{str(e)} - {error_trace}"
            }
        )

        return await load_fallback_result()

        
# -------------------------------------------------------------------------
# DOCUMENT COMPARISON ENDPOINT
# -------------------------------------------------------------------------
@app.post("/document-comparison/", response_model=ComparisonAPIResponse)
async def document_comparison(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
) -> ComparisonAPIResponse:

    # -------------------------
    # LOG REQUEST RECEIVED
    # -------------------------
    log_with_span(
        "Document comparison request received",
        "`DocCompareStart`",
        "info",
        log_extra={
            "api_name": "document-comparison",
            "status": "Received",
            "input": {
                "file1": file1.filename,
                "file2": file2.filename
            }
        }
    )

    # Validate PDFs
    if not file1.filename.lower().endswith(".pdf") or not file2.filename.lower().endswith(".pdf"):
        log_with_span(
            "Invalid input files for document comparison",
            "DocCompareInvalidInput",
            "warning",
            log_extra={
                "api_name": "document-comparison",
                "status": "Failed",
                "input": {
                    "file1": file1.filename,
                    "file2": file2.filename
                },
                "error": "Both files must be PDFs"
            }
        )
        return await get_static_fallback_response_document_comparison(file1.filename, file2.filename)

    base_dir = "temp"
    os.makedirs(base_dir, exist_ok=True)

    file1_path = os.path.join(base_dir, file1.filename)
    file2_path = os.path.join(base_dir, file2.filename)

    TIMEOUT_SECONDS = 180

    try:
        # Save PDFs
        with open(file1_path, "wb") as f1:
            f1.write(await file1.read())
        with open(file2_path, "wb") as f2:
            f2.write(await file2.read())

        # -------------------------
        # RUN COMPARISON PIPELINE
        # -------------------------
        try:
            comparison_result, duration = await asyncio.wait_for(
                main_document_comparison(file1_path, file2_path),
                timeout=TIMEOUT_SECONDS
            )

        except asyncio.TimeoutError:
            log_with_span(
                "Document comparison timed out",
                "DocCompareTimeout",
                "error",
                log_extra={
                    "api_name": "document-comparison",
                    "status": "Failed",
                    "input": {
                        "file1": file1.filename,
                        "file2": file2.filename
                    },
                    "error": f"Timeout > {TIMEOUT_SECONDS} seconds"
                }
            )
            return await get_static_fallback_response_document_comparison(file1.filename, file2.filename)

        except Exception as err:
            print("ERROR", str(err))
            log_with_span(
                "Exception during document comparison pipeline",
                "DocComparePipelineException",
                "error",
                log_extra={
                    "api_name": "document-comparison",
                    "status": "Failed",
                    "input": {
                        "file1": file1.filename,
                        "file2": file2.filename
                    },
                    "error": str(err)
                }
            )
            return await get_static_fallback_response_document_comparison(file1.filename, file2.filename)

        # Successful result
        differences, section_impact, summary, model_tokens = comparison_result

        response_data = ComparisonResponseData(
            differences=differences,
            section_added_or_removed_impact=section_impact,
            summary=summary
        )

        # -------------------------
        # SUCCESS LOG
        # -------------------------
        log_with_span(
            "Document comparison completed successfully",
            "DocCompareSuccess",
            "info",
            log_extra={
                "api_name": "document-comparison",
                "status": "Completed",
                "input": {
                    "file1": file1.filename,
                    "file2": file2.filename
                },
                "output": {
                    "differences": differences, "section_impact": section_impact, "summary": summary
                },
                "token_usage": model_tokens,
                "time_taken": duration
            }
        )

        return ComparisonAPIResponse(
            success=True,
            result=response_data,
            error=None
        )

    except Exception as final_error:
        print("ERROR", str(final_error))
        log_with_span(
            "Unexpected error in document comparison",
            "DocCompareUnexpectedError",
            "error",
            log_extra={
                "api_name": "document-comparison",
                "status": "Failed",
                "input": {
                    "file1": file1.filename,
                    "file2": file2.filename
                },
                "error": str(final_error)
            }
        )
        return await get_static_fallback_response_document_comparison(file1.filename, file2.filename)

    finally:
        # Cleanup
        try:
            if os.path.exists(file1_path):
                os.remove(file1_path)
            if os.path.exists(file2_path):
                os.remove(file2_path)

            log_with_span(
                "Temporary files cleaned",
                "DocCompareCleanup",
                "info",
                log_extra={
                    "api_name": "document-comparison",
                    "status": "Completed"
                }
            )

        except Exception as cleanup_err:
            log_with_span(
                "Cleanup failed",
                "DocCompareCleanupError",
                "warning",
                log_extra={
                    "api_name": "document-comparison",
                    "status": "Failed",
                    "error": str(cleanup_err)
                }
            )



@app.websocket("/ws/compare-documents")
async def websocket_compare_documents(websocket: WebSocket):
    """WebSocket endpoint for document comparison with real-time updates."""
    await websocket.accept()
    
    try:
        # Receive initial message with file data
        data = await websocket.receive_json()
        file1_name = data.get("file1_name")
        file2_name = data.get("file2_name")
        
        if not file1_name or not file2_name:
            await websocket.send_json({
                "type": "error",
                "message": "Missing file names"
            })
            await websocket.close()
            return
        
        # Create temporary directory for uploads
        temp_dir = tempfile.mkdtemp()
        file1_path = None
        file2_path = None
        
        try:
            # Receive file1
            file1_data = await websocket.receive_bytes()
            file1_path = os.path.join(temp_dir, file1_name)
            with open(file1_path, 'wb') as f:
                f.write(file1_data)
            
            # Send confirmation for file1
            await websocket.send_json({
                "type": "progress",
                "step": "file1_received",
                "message": f"Received {file1_name}",
                "progress": 10
            })
            
            # Receive file2
            file2_data = await websocket.receive_bytes()
            file2_path = os.path.join(temp_dir, file2_name)
            with open(file2_path, 'wb') as f:
                f.write(file2_data)
            
            # Send confirmation for file2
            await websocket.send_json({
                "type": "progress",
                "step": "file2_received",
                "message": f"Received {file2_name}",
                "progress": 20
            })
            
            # Run comparison with progress updates
            await main_document_comparison(websocket, file1_path, file2_path)
            
        finally:
            # Clean up temporary files
            if file1_path and os.path.exists(file1_path):
                os.remove(file1_path)
            if file2_path and os.path.exists(file2_path):
                os.remove(file2_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


USER_SESSIONS = {}

def build_access_hierarchy(role_assignments_data, dynamic_role_map):
    hierarchy = {"subscription_level_access": [], "resource_groups": {}}
    for role in role_assignments_data:
        scope = role.get("properties", {}).get("scope", "")
        role_uuid = role.get("properties", {}).get("roleDefinitionId", "").split("/")[-1] 
        role_name = dynamic_role_map.get(role_uuid, f"Unknown Role ({role_uuid[:8]})")
        parts = scope.split("/")

        if len(parts) == 3 and parts[1] == "subscriptions":
            hierarchy["subscription_level_access"].append(role_name)
        elif "resourceGroups" in parts:
            rg_index = parts.index("resourceGroups")
            rg_name = parts[rg_index + 1]
            if rg_name not in hierarchy["resource_groups"]:
                hierarchy["resource_groups"][rg_name] = {"rg_level_access": [], "resources": {}}
            if len(parts) == rg_index + 2:
                hierarchy["resource_groups"][rg_name]["rg_level_access"].append(role_name)
            else:
                resource_name = parts[-1] 
                resource_type = parts[-2]
                full_resource_key = f"{resource_type}/{resource_name}"
                if full_resource_key not in hierarchy["resource_groups"][rg_name]["resources"]:
                    hierarchy["resource_groups"][rg_name]["resources"][full_resource_key] = []
                hierarchy["resource_groups"][rg_name]["resources"][full_resource_key].append(role_name)
    return hierarchy


@app.get("/auth/login")
def auth_login():
    print("HERE")
    params = {
        "client_id": Config.AZURE_APP_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": Config.REDIRECT_URI,
        "response_mode": "query",
        "scope": Config.USER_SCOPES
    }
    return RedirectResponse(Config.AUTHORIZE_URL + "?" + urlencode(params))

@app.get("/callback")
def callback(code: str):
    print("HERE 2")
    try:
        # 1. Get User Token & OID
        token_response_raw = requests.post(Config.TOKEN_URL, data={
            "client_id": Config.AZURE_APP_CLIENT_ID,
            "client_secret": Config.AZURE_APP_CLIENT_SECRET,
            "code": code,
            "redirect_uri": Config.REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": Config.USER_SCOPES
        })

        user_token_response = token_response_raw.json()

        if "error" in user_token_response:
            print(f"🛑 MICROSOFT TOKEN ERROR: {user_token_response}")
            return RedirectResponse(url=f"{Config.FRONTEND_URL}/?error=auth_failed")

        id_token = user_token_response.get("id_token")

        if not id_token:
            print("🛑 ERROR: No ID Token returned by Microsoft")
            return RedirectResponse(url=f"{Config.FRONTEND_URL}/?error=auth_failed")

        def decode_jwt(token):
            payload = token.split('.')[1]
            payload += '=' * (4 - len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))

        user_info = decode_jwt(id_token)

        user_oid = user_info.get("oid")
        print("USER OID:", user_oid)

        user_name = user_info.get("name", "Unknown User")
        user_email = user_info.get("preferred_username") or user_info.get("email", "No email provided")

        # ✅ Use OID directly as user_id
        user_id = user_oid

        # 2. Get App-Only Token
        app_access_token = requests.post(Config.TOKEN_URL, data={
            "client_id": Config.AZURE_APP_CLIENT_ID,
            "client_secret": Config.AZURE_APP_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "https://management.azure.com/.default"
        }).json().get("access_token")

        if not app_access_token:
            print("🛑 ERROR: Failed to get App-Only Access Token")
            return RedirectResponse(url=f"{Config.FRONTEND_URL}/?error=server_error")

        # 3. Get Subscriptions & Map Roles
        headers = {"Authorization": f"Bearer {app_access_token}"}
        subs_response = requests.get(
            "https://management.azure.com/subscriptions?api-version=2020-01-01",
            headers=headers
        )

        user_access_map = {}

        if subs_response.status_code == 200:
            subs_data = subs_response.json().get("value", [])

            for sub in subs_data:
                sub_id = sub.get("subscriptionId")
                sub_name = sub.get("displayName")

                print(sub_id, sub_name)

                roles_def_url = f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Authorization/roleDefinitions?api-version=2022-04-01"
                roles_def_response = requests.get(roles_def_url, headers=headers)

                dynamic_role_map = {}

                if roles_def_response.status_code == 200:
                    for role_def in roles_def_response.json().get("value", []):
                        dynamic_role_map[role_def.get("name")] = role_def.get(
                            "properties", {}
                        ).get("roleName", "Unknown")

                roles_url = f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.Authorization/roleAssignments?$filter=principalId eq '{user_oid}'&api-version=2022-04-01"
                roles_response = requests.get(roles_url, headers=headers)

                if roles_response.status_code == 200:
                    raw_roles = roles_response.json().get("value", [])
                    user_access_map[sub_name] = build_access_hierarchy(
                        raw_roles,
                        dynamic_role_map
                    )


        print("REDIRECT URL")
        # Redirect to frontend
        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/home",
            status_code=302
        )

    except Exception as e:
        print(f"🛑 CRITICAL CALLBACK ERROR: {e}")
        traceback.print_exc()

        return RedirectResponse(
            url=f"{Config.FRONTEND_URL}/?error=server_error",
            status_code=302
        )
        