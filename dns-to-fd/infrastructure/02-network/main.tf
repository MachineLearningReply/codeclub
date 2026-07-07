locals {
  project      = "dnstofd"
  rg           = "codeclub"
  location     = "Germany West Central"
  app          = "d6e0c517-7a34-4b6c-9688-48557307eb1a"
  sp           = "cf0a2cdc-2be7-498b-9392-edcc1f5581d2"
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
    key                  = "02.network.tfstate"
  }
}

provider "azurerm" {
  subscription_id = local.subscription
  features {}
}

resource "azurerm_virtual_network" "main" {
  name                = "${local.project}-vnet"
  resource_group_name = local.rg
  location            = local.location
  address_space       = ["10.42.0.0/16"]
}

resource "azurerm_subnet" "aks" {
  name                 = "${local.project}-snet-aks"
  resource_group_name  = local.rg
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.42.0.0/22"]
}

resource "azurerm_subnet" "app_gateway" {
  name                 = "${local.project}-snet-appgw"
  resource_group_name  = local.rg
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.42.4.0/24"]
}

resource "azurerm_subnet" "private_endpoints" {
  address_prefixes     = ["10.42.5.0/27"]
  name                 = "${local.project}-snet-pe"
  resource_group_name  = local.rg
  virtual_network_name = azurerm_virtual_network.main.name
}

resource "azurerm_subnet" "demo" {
  address_prefixes     = ["10.42.5.32/27"]
  name                 = "${local.project}-snet-demo"
  resource_group_name  = local.rg
  virtual_network_name = azurerm_virtual_network.main.name
}


output "vnet_id" {
  value = azurerm_virtual_network.main.id
}

output "vnet_name" {
  value = azurerm_virtual_network.main.name
}

output "aks_subnet_id" {
  value = azurerm_subnet.aks.id
}

output "app_gateway_subnet_id" {
  value = azurerm_subnet.app_gateway.id
}

output "private_endpoints_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "demo_subnet_id" {
  value = azurerm_subnet.demo.id
}

output "subnet_ids" {
  value = {
    aks               = azurerm_subnet.aks.id
    app_gateway       = azurerm_subnet.app_gateway.id
    private_endpoints = azurerm_subnet.private_endpoints.id
    demo              = azurerm_subnet.demo.id
  }
}
