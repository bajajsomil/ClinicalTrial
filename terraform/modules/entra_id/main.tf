provider "azuread" {}

# ============================
# Variables
# ============================
variable "redirect_uris" {
  description = "List of redirect URIs for the application"
  type        = list(string)
}

variable "app_name" {
  description = "Name of the Entra ID application"
  type        = string
  default     = "ClinicalTrialapp09198578"
}

variable "secret_expiry_date" {
  description = "Client secret hard expiry date in RFC3339 format"
  type        = string
  default     = "2026-12-31T23:59:59Z"
}

# ============================
# Data (Tenant Info)
# ============================
data "azuread_client_config" "current" {}

# ============================
# Azure AD Application
# ============================
resource "azuread_application" "app" {
  display_name = var.app_name
  
  # FIX: Explicitly assign the Terraform runner as the owner
  owners       = [data.azuread_client_config.current.object_id]

  web {
    redirect_uris = var.redirect_uris

    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = true
    }
  }

  # Microsoft Graph API permissions
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    # User.Read — Delegated scope
    resource_access {
      id   = "e1fe6dd8-ba39-40d6-baa8-502871459f93"
      type = "Scope"
    }

    # User.ReadAll — Application role
    resource_access {
      id   = "df021288-bdef-4463-88db-98f22de89214"
      type = "Role"
    }
  }
}

# ============================
# Service Principal
# ============================
resource "azuread_service_principal" "sp" {
  client_id = azuread_application.app.client_id
  
  # FIX: Assign owner and explicitly disable role assignment requirement
  owners                       = [data.azuread_client_config.current.object_id]
  app_role_assignment_required = false
}

# ============================
# Client Secret
# ============================
resource "azuread_application_password" "secret" {
  application_id = azuread_application.app.id
  display_name   = "ClinicalAppSecret"
  end_date       = var.secret_expiry_date
}

# ============================
# Outputs
# ============================
output "client_id" {
  description = "Application (client) ID"
  value       = azuread_application.app.client_id
}

output "object_id" {
  description = "Application object ID"
  value       = azuread_application.app.object_id
}

output "client_secret" {
  description = "Client secret value"
  value       = azuread_application_password.secret.value
  sensitive   = true
}

output "tenant_id" {
  description = "Azure tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}