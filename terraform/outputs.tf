output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "container_app_url" {
  description = "Public URL of the Container App (use as BASE_URL)"
  value       = module.container_app.fqdn
}

output "storage_account_name" {
  value = module.storage.account_name
}

output "appinsights_connection_string" {
  value     = module.monitoring.connection_string
  sensitive = true
}

