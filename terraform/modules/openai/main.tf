variable "resource_group_name" { type = string }
variable "location" { type = string }
 
resource "azurerm_cognitive_account" "openai" {
  name                = "clinicalTrialopenaiknv123987"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0"
 
  tags = {
    costcenter = "500"
    workload   = "sandbox"
  }
}
 
resource "azurerm_cognitive_deployment" "gpt41" {
  name                 = "gpt41"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4.1"
    version = "2025-04-14" 
  }
  sku {
    name     = "GlobalStandard"
    capacity =  40
  }
}
 
resource "azurerm_cognitive_deployment" "gpt41_mini" {
  name                 = "gpt41_mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4.1-mini"
    version = "2025-04-14" 
  }
  sku {
    name     = "GlobalStandard"
    capacity = 40
  }
}
 
resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
  sku {
    name     = "Standard"
    capacity = 40
  }
}
 
resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt4o_mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }
  sku {
    name     = "GlobalStandard" 
    capacity = 40
 
  }
}
 
output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}
output "openai_api_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}
output "openai_api_version" {
  value = "2024-02-15-preview"
}