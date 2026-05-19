import os
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobClient, ContentSettings
from config.config import Config
from src.adapters.logger import log_with_span
from src.processes.protocol_analyzer.models import BlobUploadInput


class AzureBlob:
    """
    Wrapper class for Azure Blob Storage operations.
    Provides functionality to initialize blob clients and upload files.
    """

    def __init__(self) -> None:
        """
        Initialize the AzureBlob instance with a connection string.
        Creates a BlobServiceClient for further operations.
        """
        self.connection_string: str = Config.blob_connection_string
        self.blob_service_client: BlobServiceClient = (
            BlobServiceClient.from_connection_string(self.connection_string)
        )

    def initialize_blob_client(self, container_name: str, file_name: str) -> Optional[BlobClient]:
        """
        Initialize a BlobClient for a specific container and blob.

        Args:
            container_name (str): The name of the Azure Blob container.
            file_name (str): The name of the file/blob in the container.

        Returns:
            Optional[BlobClient]: An instance of BlobClient if successful, else None.
        """
        try:
            blob_client: BlobClient = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=file_name
            )
            log_with_span("[INFO] Blob Client created successfully.", "Blob", "info", log_extra={'service_name': 'Azure Blob','input': f"Container Name - {container_name} , Blob - {file_name}", 'status': 'Success'})
            return blob_client
        except Exception as e:
            log_with_span(
                f"Error in initialize_blob_client() while initializing blob client", "Blob", "error", log_extra={'service_name': 'Azure Blob','input': f"Container Name - {container_name} , Blob - {file_name}", 'status': 'Failed', 'error': str(e)}
            )
            return None

    def upload_blob(self, upload_input: BlobUploadInput) -> bool:
        """
        Upload a file to Azure Blob Storage.

        Args:
            upload_input (BlobUploadInput): Pydantic model containing:
                - container_name (str): Target Azure Blob container.
                - filepath (str): Local directory path of the file.
                - file_name (str): File name to be uploaded.

        Returns:
            bool: True if upload is successful, False otherwise.
        """
        try:
            blob_client = self.initialize_blob_client(
                upload_input.container_name,
                upload_input.file_name
            )
            if not blob_client:
                return False

            file_path = os.path.join(upload_input.filepath, upload_input.file_name)
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/pdf")
                )

            log_with_span(
                "File Uploaded Successfully", "Blob", "info", log_extra={'service_name': 'Azure Blob','input': upload_input.model_dump(), 'status': 'Success'}
            )
            return True
        except Exception as e:
            log_with_span(
                "Error Uploading File in Blob", "Blob", "error", log_extra={'service_name': 'Azure Blob','input': upload_input.model_dump(), 'status': 'Failed', 'error': str(e)}
            )
            return False


# Singleton instance
azure_blob = AzureBlob()
