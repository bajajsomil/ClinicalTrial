/**
 * Central API configuration.
 *
 * All backend URLs are derived from VITE_API_BASE_URL defined in `.env`.
 * To point the frontend at a different backend, only change that one variable.
 *
 * Example .env:
 *   VITE_API_BASE_URL=http://localhost:8000       # local dev
 *   VITE_API_BASE_URL=https://api.myapp.com       # production
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

/**
 * Converts the HTTP(S) base URL into a WebSocket (ws/wss) URL.
 * e.g. "http://localhost:8000"  → "ws://localhost:8000"
 *      "https://api.myapp.com" → "wss://api.myapp.com"
 */
export const getWsBaseUrl = (): string =>
  API_BASE_URL.replace(/^http/, "ws");

export const BLOB_URL: string =
  import.meta.env.VITE_PHARMA_CONTAINER_URL ?? "https://cofrablob.blob.core.windows.net/pharma/";

/**
 * Fetches the Azure Storage Service SAS token for the container from the backend.
 */
export const fetchContainerSasToken = async (): Promise<string> => {
  try {
    const response = await fetch(`${API_BASE_URL}/sas-token`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.sas_token || "";
  } catch (error) {
    console.error("Failed to fetch SAS token from backend:", error);
    return "";
  }
};
