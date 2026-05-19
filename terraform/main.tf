provider "azurerm" {
  features {}
}

provider "azuread" {}

# FIXED: Resource Group name matches deploy.sh exactly
resource "azurerm_resource_group" "rg" {
  name     = "clinical-trial123654"
  location = "australiaeast"
}

module "openai" {
  source              = "./modules/openai"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

module "docintel" {
  source              = "./modules/doc_intelligence"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

module "entra_id" {
  source = "./modules/entra_id"

  # We only put localhost here to avoid a Terraform Circular Dependency.
  # The deploy.sh script will dynamically append the cloud URL later.
  redirect_uris = [
    "http://localhost:8000/callback",
  ]
}

module "app_service" {
  source              = "./modules/app_service"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  openai_endpoint           = module.openai.openai_endpoint
  openai_api_key            = module.openai.openai_api_key
  docintel_endpoint         = module.docintel.formrecognizer_endpoint
  docintel_api_key          = module.docintel.formrecognizer_api_key
  storage_account_name      = module.storage.storage_account_name
  storage_access_key        = module.storage.storage_primary_access_key
  storage_connection_string = module.storage.storage_connection_string

  # Passing Entra ID credentials down to the Container App
  azure_client_id     = module.entra_id.client_id
  azure_tenant_id     = module.entra_id.tenant_id
  azure_client_secret = module.entra_id.client_secret
}

resource "local_file" "combined_env" {
  filename = "${path.module}/.env"

  content = <<-EOT
# OpenAI Credentials
OPENAI_ENDPOINT=${module.openai.openai_endpoint}
OPENAI_API_KEY=${module.openai.openai_api_key}
OPENAI_API_VERSION=${module.openai.openai_api_version}

# Document Intelligence Credentials
DOCINTEL_ENDPOINT=${module.docintel.formrecognizer_endpoint}
DOCINTEL_API_KEY=${module.docintel.formrecognizer_api_key}
DOCINTEL_API_VERSION=${module.docintel.formrecognizer_api_version}

# Storage Account Credentials
STORAGE_ACCOUNT_NAME=${module.storage.storage_account_name}
STORAGE_ACCOUNT_KEY=${module.storage.storage_primary_access_key}
STORAGE_CONNECTION_STRING=${module.storage.storage_connection_string}

# Entra ID Credentials
ENTRA_CLIENT_ID=${module.entra_id.client_id}
ENTRA_TENANT_ID=${module.entra_id.tenant_id}

# App Service URLs
BACKEND_URL=https://${module.app_service.backend_hostname}
FRONTEND_URL=https://${module.app_service.frontend_hostname}
EOT
}

output "backend_hostname" {
  description = "The hostname of the backend App Service"
  value       = module.app_service.backend_hostname
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = module.storage.storage_account_name
}

output "frontend_hostname" {
  description = "The hostname of the frontend App Service"
  value       = module.app_service.frontend_hostname
}

output "entra_client_id" {
  description = "Entra ID application client ID"
  value       = module.entra_id.client_id
}

output "entra_tenant_id" {
  description = "Azure tenant ID"
  value       = module.entra_id.tenant_id
}