terraform {
  required_version = "~> 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Remote state in Azure Blob (create this manually once, see docs/getting_started.md)
  backend "azurerm" {
    resource_group_name  = "linkpulse-tfstate-rg"
    storage_account_name = "linkpulsetfstate"
    container_name       = "tfstate"
    key                  = "linkpulse.main.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# ── Child modules (from linkpulse-tf-modules repo) ──────────────────────

module "storage" {
  source = "git::https://github.com/ktnsh24/linkpulse-tf-modules.git//modules/storage?ref=main"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  tags                = local.common_tags
}

module "monitoring" {
  source = "git::https://github.com/ktnsh24/linkpulse-tf-modules.git//modules/monitoring?ref=main"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  tags                = local.common_tags
}

module "container_app" {
  source = "git::https://github.com/ktnsh24/linkpulse-tf-modules.git//modules/container_app?ref=main"

  resource_group_name              = azurerm_resource_group.main.name
  location                         = azurerm_resource_group.main.location
  project                          = var.project
  environment                      = var.environment
  container_image                  = var.container_image
  azure_storage_connection_string  = module.storage.connection_string
  appinsights_connection_string    = module.monitoring.connection_string
  tags                             = local.common_tags
}

# ── Resource Group ──────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = "${var.project}-rg-${var.environment}"
  location = var.location
  tags     = local.common_tags
}

# ── Common tags ─────────────────────────────────────────────────────────

locals {
  common_tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
    repository  = "linkpulse"
  }
}

