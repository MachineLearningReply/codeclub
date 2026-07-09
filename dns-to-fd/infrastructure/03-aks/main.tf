locals {
  project      = "dnstofd"
  rg           = "codeclub"
  location     = "Germany West Central"
  subscription = "b77552dc-be0b-4676-8373-98fd6ff60759"

  user = "fah.ahmed@reply.de"
  tags = {
    user     = local.user
    project  = local.project
    validity = "7"
  }
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
    key                  = "03.aks.tfstate"
  }
}

provider "azurerm" {
  subscription_id = local.subscription
  features {}
}

data "terraform_remote_state" "bootstrap" {
  backend = "azurerm"

  config = {
    use_oidc             = true
    use_azuread_auth     = true
    storage_account_name = "codeclubtfstate"
    container_name       = "tfstate"
    key                  = "01.terraform.tfstate"
  }
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

data "azurerm_container_registry" "acr" {
  name                = data.terraform_remote_state.bootstrap.outputs.acr_name
  resource_group_name = local.rg
}

resource "azurerm_user_assigned_identity" "aks_control_plane" {
  name                = "${local.project}-aks-cp-mi"
  location            = local.location
  resource_group_name = local.rg
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "aks_kubelet" {
  name                = "${local.project}-aks-kubelet-mi"
  location            = local.location
  resource_group_name = local.rg
  tags                = local.tags
}

resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                            = data.terraform_remote_state.network.outputs.vnet_id
  role_definition_name             = "Network Contributor"
  principal_id                     = azurerm_user_assigned_identity.aks_control_plane.principal_id
  skip_service_principal_aad_check = true
}


resource "azurerm_role_assignment" "aks_operator" {
  scope                            = azurerm_user_assigned_identity.aks_kubelet.id
  role_definition_name             = "Managed Identity Operator"
  principal_id                     = azurerm_user_assigned_identity.aks_control_plane.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "kubelet_acr_pull" {
  principal_id                     = azurerm_user_assigned_identity.aks_kubelet.principal_id
  scope                            = data.azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
  role_definition_name             = "AcrPull"
}

resource "azurerm_role_assignment" "agic_app_gateway_subnet_network_contributor" {
  scope                            = data.terraform_remote_state.network.outputs.vnet_id
  role_definition_name             = "Network Contributor"
  principal_id                     = azurerm_kubernetes_cluster.dnstofd.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id
  skip_service_principal_aad_check = true
}

resource "azurerm_kubernetes_cluster" "dnstofd" {
  name                = "${local.project}-aks"
  location            = local.location
  resource_group_name = local.rg
  dns_prefix          = "${local.project}aks"

  sku_tier = "Free"

  node_resource_group = "${local.project}-aks-nodes-rg"

  default_node_pool {
    name           = "default"
    node_count     = 2
    vm_size        = "Standard_D2ls_v5"
    os_sku         = "Ubuntu"
    vnet_subnet_id = data.terraform_remote_state.network.outputs.aks_subnet_id
    tags           = local.tags

    upgrade_settings {
      drain_timeout_in_minutes      = 0
      max_surge                     = "10%"
      node_soak_duration_in_minutes = 0
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_control_plane.id]
  }

  kubelet_identity {
    client_id                 = azurerm_user_assigned_identity.aks_kubelet.client_id
    object_id                 = azurerm_user_assigned_identity.aks_kubelet.principal_id
    user_assigned_identity_id = azurerm_user_assigned_identity.aks_kubelet.id
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }

  ingress_application_gateway {
    gateway_name = "${local.project}-appgw"
    subnet_id    = data.terraform_remote_state.network.outputs.app_gateway_subnet_id
  }

  role_based_access_control_enabled = true
  oidc_issuer_enabled               = true

  tags = local.tags


  depends_on = [
    azurerm_role_assignment.aks_operator,
    azurerm_role_assignment.aks_network_contributor,
    azurerm_role_assignment.kubelet_acr_pull
  ]

}

output "aks_id" {
  value = azurerm_kubernetes_cluster.dnstofd.id
}

output "aks_name" {
  value = azurerm_kubernetes_cluster.dnstofd.name
}

output "node_resource_group" {
  value = azurerm_kubernetes_cluster.dnstofd.node_resource_group
}

output "app_gateway_id" {
  value = azurerm_kubernetes_cluster.dnstofd.ingress_application_gateway[0].effective_gateway_id
}

output "control_plane_identity_id" {
  value = azurerm_user_assigned_identity.aks_control_plane.id
}

output "kubelet_identity_id" {
  value = azurerm_user_assigned_identity.aks_kubelet.id
}
