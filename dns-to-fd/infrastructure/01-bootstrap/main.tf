locals {
  project = "dnstofd"
  rg = "codeclub"
  location = "Germany West Central"
  app = "d6e0c517-7a34-4b6c-9688-48557307eb1a"
  sp = "cf0a2cdc-2be7-498b-9392-edcc1f5581d2"
  subscription = "b77552dc-be0b-4676-8373-98fd6ff60759"
}


terraform {
  required_providers {
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
    key                  = "01.terraform.tfstate"
  }
}

provider "azurerm" {
  subscription_id = local.subscription
  features {}
}


resource "azurerm_container_registry" "acr" {
  name                = local.project
  resource_group_name = local.rg
  location            = local.location
  sku                 = "Basic"
  admin_enabled       = false
  public_network_access_enabled = true
}

resource "azurerm_role_assignment" "acr_push" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPush"
  principal_id         = local.sp
  principal_type = "ServicePrincipal"
}


resource "azurerm_storage_account" "blob_storage" {
  name                     = "dnstofd"
  resource_group_name      = local.rg
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_postgresql_flexible_server" "db_server" {
  name = local.project
  resource_group_name = local.rg
  location = local.location
  administrator_login = "psqladmin"
  administrator_password = var.db_admin_password
  zone = "1"
  version = "13"
  sku_name = "B_Standard_B1ms"
  storage_mb = 32768

  public_network_access_enabled = true
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = "${local.project}-db"
  server_id = azurerm_postgresql_flexible_server.db_server.id
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "storage_account_url" {
  value = azurerm_storage_account.blob_storage.primary_blob_endpoint
}

output "storage_conn_string" {
  value = azurerm_storage_account.blob_storage.primary_blob_connection_string
  sensitive = true
}

output "db_server_url" {
  value = azurerm_postgresql_flexible_server.db_server.fqdn
}

output "db" {
  value = azurerm_postgresql_flexible_server_database.db.name
}