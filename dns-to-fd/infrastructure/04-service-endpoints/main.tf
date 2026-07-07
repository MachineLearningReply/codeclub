locals {
  project      = "dnstofd"
  rg           = "codeclub"
  location     = "Germany West Central"
  subscription = "b77552dc-be0b-4676-8373-98fd6ff60759"

  storage_account_name = local.project
  storage_account_id   = "/subscriptions/${local.subscription}/resourceGroups/${local.rg}/providers/Microsoft.Storage/storageAccounts/${local.storage_account_name}"

  service_endpoint_subnet_ids = {
    aks  = data.terraform_remote_state.network.outputs.aks_subnet_id
    demo = data.terraform_remote_state.network.outputs.demo_subnet_id
  }
}

terraform {
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = "~> 1.15"
    }

    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.1.0"
    }
  }

  backend "azurerm" {
    use_oidc             = true
    use_azuread_auth     = true
    storage_account_name = "codeclubtfstate"
    container_name       = "tfstate"
    key                  = "04.service-endpoints.tfstate"
  }
}

provider "azapi" {}

provider "azurerm" {
  subscription_id = local.subscription
  features {}
}

data "terraform_remote_state" "network" {
  backend = "azurerm"

  config = {
    use_oidc             = true
    use_azuread_auth     = true
    storage_account_name = "codeclubtfstate"
    container_name       = "tfstate"
    key                  = "02.network.tfstate"
  }
}

resource "azapi_update_resource" "storage_service_endpoints" {
  for_each = local.service_endpoint_subnet_ids

  type        = "Microsoft.Network/virtualNetworks/subnets@2023-09-01"
  resource_id = each.value

  body = jsonencode({
    properties = {
      serviceEndpoints = [
        {
          service = "Microsoft.Storage"
        }
      ]
    }
  })
}

resource "azurerm_storage_account_network_rules" "blob_storage" {
  storage_account_id = local.storage_account_id

  default_action             = "Deny"
  bypass                     = ["AzureServices"]
  virtual_network_subnet_ids = values(local.service_endpoint_subnet_ids)

  depends_on = [azapi_update_resource.storage_service_endpoints]
}

output "storage_service_endpoint_subnet_ids" {
  value = local.service_endpoint_subnet_ids
}

output "storage_public_endpoint" {
  value = "https://${local.storage_account_name}.blob.core.windows.net/"
}

output "postgres_service_endpoint_note" {
  value = "Azure Database for PostgreSQL Flexible Server does not expose Storage-style VNet service endpoint rules in this stack; use 05-private-endpoints for private PostgreSQL access."
}
