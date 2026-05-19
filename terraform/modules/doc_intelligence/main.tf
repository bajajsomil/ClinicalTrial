variable "resource_group_name" { type = string }
variable "location" { type = string }

resource "azurerm_cognitive_account" "formrecognizer" {
  name                = "clinicalTrialdocintel123654"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "FormRecognizer"
  sku_name            = "S0"

  tags = {
    costcenter = "500"
    workload   = "sandbox"
  }
}

variable "docintel_api_version" {
  default = "2023-10-01"
}

output "formrecognizer_endpoint" {
  value = azurerm_cognitive_account.formrecognizer.endpoint
}
output "formrecognizer_api_key" {
  value     = azurerm_cognitive_account.formrecognizer.primary_access_key
  sensitive = true
}
output "formrecognizer_api_version" {
  value = var.docintel_api_version
}
