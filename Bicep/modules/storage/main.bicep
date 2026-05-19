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

// --- Outputs ---

output storage_account_name string = storageAccount.name

// Retrieve the primary key using listKeys()
var storageKey = storageAccount.listKeys().keys[0].value
output storage_primary_access_key string = storageKey

// Construct the connection string manually
output storage_connection_string string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageKey};EndpointSuffix=${environment().suffixes.storage}'

