locals {
  project      = "dnstofd"
  rg           = "codeclub"
  location     = "Germany West Central"
  subscription = "b77552dc-be0b-4676-8373-98fd6ff60759"

  storage_account_id = "/subscriptions/${local.subscription}/resourceGroups/${local.rg}/providers/Microsoft.Storage/storageAccounts/${local.project}"
  postgres_server_id = "/subscriptions/${local.subscription}/resourceGroups/${local.rg}/providers/Microsoft.DBforPostgreSQL/flexibleServers/${local.project}"
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
    key                  = "05.private-endpoints.tfstate"
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

resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = local.rg
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  name                  = "${local.project}-blob-dns-link"
  resource_group_name   = local.rg
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = data.terraform_remote_state.network.outputs.vnet_id
}

resource "azurerm_private_endpoint" "blob" {
  name                = "${local.project}-blob-pe"
  location            = local.location
  resource_group_name = local.rg
  subnet_id           = data.terraform_remote_state.network.outputs.private_endpoints_subnet_id

  private_service_connection {
    name                           = "${local.project}-blob-psc"
    private_connection_resource_id = local.storage_account_id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = local.rg
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${local.project}-postgres-dns-link"
  resource_group_name   = local.rg
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = data.terraform_remote_state.network.outputs.vnet_id
}

resource "azurerm_private_endpoint" "postgres" {
  name                = "${local.project}-postgres-pe"
  location            = local.location
  resource_group_name = local.rg
  subnet_id           = data.terraform_remote_state.network.outputs.private_endpoints_subnet_id

  private_service_connection {
    name                           = "${local.project}-postgres-psc"
    private_connection_resource_id = local.postgres_server_id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.postgres.id]
  }
}

resource "azapi_update_resource" "disable_storage_public_network_access" {
  type        = "Microsoft.Storage/storageAccounts@2023-01-01"
  resource_id = local.storage_account_id

  body = jsonencode({
    properties = {
      publicNetworkAccess = "Disabled"
    }
  })

  depends_on = [azurerm_private_endpoint.blob]
}

resource "azapi_update_resource" "disable_postgres_public_network_access" {
  type        = "Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01"
  resource_id = local.postgres_server_id

  body = jsonencode({
    properties = {
      publicNetworkAccess = "Disabled"
    }
  })

  depends_on = [azurerm_private_endpoint.postgres]
}

output "blob_private_endpoint_ip" {
  value = azurerm_private_endpoint.blob.private_service_connection[0].private_ip_address
}

output "postgres_private_endpoint_ip" {
  value = azurerm_private_endpoint.postgres.private_service_connection[0].private_ip_address
}

output "blob_private_dns_zone" {
  value = azurerm_private_dns_zone.blob.name
}

output "postgres_private_dns_zone" {
  value = azurerm_private_dns_zone.postgres.name
}
