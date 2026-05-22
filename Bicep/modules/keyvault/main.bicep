@description('The name of the Key Vault.')
param vaultName string

@description('The Azure location for the resources.')
param location string = resourceGroup().location

@description('The principal ID of the Managed Identity to grant Secrets User access.')
param principalId string

@description('The Object ID of the deployer to grant Secrets Officer access.')
param currentUserId string

@description('Optional: Subnet ID for the Private Endpoint.')
param subnetId string = ''

@description('Optional: Private DNS Zone ID for Key Vault.')
param dnsZoneId string = ''

@description('Optional: Log Analytics Workspace ID for diagnostic settings.')
param logAnalyticsWorkspaceId string = ''

// --- Key Vault ---
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    publicNetworkAccess: 'Disabled'
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// --- Secrets (Placeholder to prevent App reference errors before deployment script seeds real value) ---
resource entraSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'entra-client-secret'
  properties: {
    value: 'placeholder-secret'
  }
}

// --- Private Endpoint for Key Vault ---
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(subnetId)) {
  name: '${vaultName}-private-endpoint'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${vaultName}-link-connection'
        properties: {
          privateLinkServiceId: vault.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

// --- Private DNS Zone Group for Key Vault ---
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (!empty(subnetId) && !empty(dnsZoneId)) {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'keyvault-dns-config'
        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

// --- RBAC: Secrets User for Managed Identity ---
resource secretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(vault.id, principalId, 'Key Vault Secrets User')
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633014f-17de-419a-b87d-4885ed2ac485')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

// --- RBAC: Secrets Officer for Deployer (to seed/update secrets via CLI) ---
resource secretsOfficerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(currentUserId)) {
  name: guid(vault.id, currentUserId, 'Key Vault Secrets Officer')
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
    principalId: currentUserId
    principalType: 'ServicePrincipal'
  }
}

// --- Diagnostic Settings ---
resource vaultDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${vaultName}-diagnostics'
  scope: vault
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'AuditEvent'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

output vaultUri string = vault.properties.vaultUri
