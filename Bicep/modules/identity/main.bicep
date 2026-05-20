@description('Location for all resources.')
param location string = resourceGroup().location

@description('The base name to construct identity name dynamically')
param baseName string

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${baseName}-identity'
  location: location
}

output id string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
