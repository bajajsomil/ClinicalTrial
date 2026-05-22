@description('Location for the storage account.')
param location string = resourceGroup().location

@description('Optional: Subnet ID for the Private Endpoint')
param subnetId string = ''

@description('Optional: Private DNS Zone ID for Blob Storage')
param dnsZoneId string = ''

@description('Public network access status for the Storage Account')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Disabled'

@description('The name of the storage account.')
param storageAccountName string = 'clinicaltrialstore909'

@description('Optional: The principal ID of the Managed Identity to assign roles to.')
param principalId string = ''

@description('Optional: Set to true to create role assignments for Managed Identity.')
param createRoleAssignments bool = false

@description('Optional: Log Analytics Workspace ID for diagnostic settings.')
param logAnalyticsWorkspaceId string = ''

// --- Storage Account ---
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: publicNetworkAccess
  }
  tags: {
    workload: 'sandbox'
  }
}

// --- Blob Services (Required parent for containers) ---
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// --- Storage Container ---
resource pharmaContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'pharma'
  properties: {
    publicAccess: 'None'
  }
}

// --- Private Endpoint for Storage ---
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(subnetId)) {
  name: 'storage-private-endpoint'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'storage-link-connection'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

// --- Private DNS Zone Group for Storage ---
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (!empty(subnetId) && !empty(dnsZoneId)) {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'storage-dns-config'
        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId) && createRoleAssignments) {
  name: guid(storageAccount.id, principalId, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Diagnostic Settings ---
resource storageDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${storageAccountName}-diagnostics'
  scope: storageAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      {
        category: 'Transaction'
        enabled: true
      }
    ]
  }
}

resource blobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${storageAccountName}-blob-diagnostics'
  scope: blobServices
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'StorageRead'
        enabled: true
      }
      {
        category: 'StorageWrite'
        enabled: true
      }
      {
        category: 'StorageDelete'
        enabled: true
      }
    ]
  }
}

// --- Outputs ---

output storage_account_name string = storageAccount.name
