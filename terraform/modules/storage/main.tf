variable "resource_group_name" { type = string }
variable "location" { type = string }

resource "azurerm_storage_account" "storage" {
  name                            = "clinicaltrialstore123654" 
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = true 

  tags = {
    workload = "sandbox"
  }
}

resource "azurerm_storage_container" "pharma" {
  name                  = "pharma"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "container" 
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}
output "storage_primary_access_key" {
  value     = azurerm_storage_account.storage.primary_access_key
  sensitive = true
}
output "storage_connection_string" {
  value     = azurerm_storage_account.storage.primary_connection_string
  sensitive = true
}
