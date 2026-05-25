@description('Location for the storage account.')
param location string = resourceGroup().location


@description('Public network access status for the Storage Account')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('The name of the storage account.')
param storageAccountName string = 'clinicaltrialstore909'

@description('Optional: The principal ID of the Managed Identity to assign roles to.')
param principalId string = ''

@description('Optional: Set to true to create role assignments for Managed Identity.')
param createRoleAssignments bool = false

// --- Storage Account ---
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: true
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
    publicAccess: 'Blob'
  }
}



resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId) && createRoleAssignments) {
  name: guid(storageAccount.id, principalId, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92e5b2-2d11-453d-a403-e96b0029c9fe')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

// --- Outputs ---

output storage_account_name string = storageAccount.name

// Retrieve the primary key using listKeys()
var storageKey = storageAccount.listKeys().keys[0].value
output storage_primary_access_key string = storageKey

// Construct the connection string manually
output storage_connection_string string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageKey};EndpointSuffix=${environment().suffixes.storage}'

