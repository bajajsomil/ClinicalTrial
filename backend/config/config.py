import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    TAVILY_API_KEY=""
    
    # ===== OpenAI =====
    AZURE_OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
    # REMOVED: AZURE_OPENAI_KEY (Using Managed Identity)
    AZURE_OPENAI_VERSION = os.getenv("OPENAI_API_VERSION", "2024-12-01-preview")

    # ===== Document Intelligence =====
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("DOCINTEL_ENDPOINT")
    # REMOVED: AZURE_DOCUMENT_INTELLIGENCE_KEY (Using Managed Identity)

    # ===== Storage =====
    # REMOVED: blob_connection_string 
    # ADDED: Storage Account Name (needed to construct the URL for Managed Identity)
    storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME") 
    blob_container_name = "pharma"  # keep static

    # ===== Entra ID (Human OAuth2 Flow) =====
    # KEPT: We still need these to authenticate humans logging into the UI
    AZURE_APP_CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
    AZURE_APP_CLIENT_SECRET = os.getenv("ENTRA_CLIENT_SECRET")
    AZURE_TENANT_ID = os.getenv("ENTRA_TENANT_ID")

    # ===== URLs =====
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

    # ===== Derived =====
    REDIRECT_URI = f"{BACKEND_URL}/callback"
    AUTHORIZE_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize"
    TOKEN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"

    # ===== Models (keep static) =====
    GPT_GENERATION_4O_MODEL = "gpt4o"
    GPT_GENERATION_4O_MINI_MODEL = "gpt4o_mini"
    GPT_GENERATION_4i_MINI = "gpt41_mini"
    GPT_GENERATION_4i = "gpt41"

    USER_SCOPES = "openid profile email"