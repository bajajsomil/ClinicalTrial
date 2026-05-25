import os
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContentSettings
from config.config import Config
from src.adapters.logger import log_with_span
from src.processes.protocol_analyzer.models import BlobUploadInput
from datetime import datetime, timedelta, timezone
from azure.storage.blob import generate_container_sas, ContainerSasPermissions


class AzureBlob:
    """
    Wrapper class for Azure Blob Storage operations.
    Provides functionality to initialize blob clients and upload files using Managed Identity.
    """

    def __init__(self) -> None:
        """
        Initialize the AzureBlob instance using DefaultAzureCredential.
        Creates a BlobServiceClient for further operations without using a connection string.
        """
        # Fetch the storage account name from your config instead of a connection string
        self.storage_account_name: str = Config.storage_account_name
        self.account_url: str = f"https://{self.storage_account_name}.blob.core.windows.net"
        
        # DefaultAzureCredential automatically picks up the Managed Identity 
        # in Container Apps or your local Azure CLI credentials during local dev
        self.credential = DefaultAzureCredential()

        self.blob_service_client: BlobServiceClient = BlobServiceClient(
            account_url=self.account_url,
            credential=self.credential
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
                f"Error Uploading File in Blob {e}", "Blob", "error", log_extra={'service_name': 'Azure Blob','input': upload_input.model_dump(), 'status': 'Failed', 'error': str(e)}
            )
            return False

    def generate_sas_token(self, container_name: str) -> str:
        """
        Generate a container SAS token using User Delegation Key (via DefaultAzureCredential).
        """
        
        try:
            # Expiry 24 hours from now
            start_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)

            # 1. Get a user delegation key
            user_delegation_key = self.blob_service_client.get_user_delegation_key(
                key_start_time=start_time,
                key_expiry_time=expiry_time
            )

            # 2. Generate container SAS token
            sas_token = generate_container_sas(
                account_name=self.storage_account_name,
                container_name=container_name,
                user_delegation_key=user_delegation_key,
                permission=ContainerSasPermissions(read=True),
                expiry=expiry_time,
                start=start_time
            )
            
            return sas_token
        except Exception as e:
            log_with_span(
                f"Error generating SAS token: {e}", 
                "BlobSAS", 
                "error", 
                log_extra={
                    'service_name': 'Azure Blob',
                    'container_name': container_name,
                    'status': 'Failed',
                    'error': str(e)
                }
            )
            raise e


# Singleton instance
azure_blob = AzureBlob()