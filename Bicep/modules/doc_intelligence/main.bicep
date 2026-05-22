@description('Location for all resources.')
param location string = resourceGroup().location

@description('API version for the Document Intelligence service.')
param docintel_api_version string = '2023-10-01'

@description('The name of the Document Intelligence resource.')
param docintelName string = 'clinicalTrialdocintel909'

@description('Optional: The principal ID of the Managed Identity to assign roles to.')
param principalId string = ''

@description('Optional: Set to true to create role assignments for Managed Identity.')
param createRoleAssignments bool = false

@description('Optional: Subnet ID for the Private Endpoint')
param subnetId string = ''

@description('Optional: Private DNS Zone ID for Cognitive Services')
param dnsZoneId string = ''

@description('Optional: Log Analytics Workspace ID for diagnostic settings.')
param logAnalyticsWorkspaceId string = ''

resource formrecognizer 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: docintelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  tags: {
    costcenter: '500'
    workload: 'sandbox'
  }
  properties: {
    customSubDomainName: toLower(docintelName)
    publicNetworkAccess: 'Disabled'
  }
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId) && createRoleAssignments) {
  name: guid(formrecognizer.id, principalId, 'Cognitive Services User')
  scope: formrecognizer
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b40fb-5815-43a2-ac46-92c12159d690')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(subnetId)) {
  name: 'docintel-private-endpoint'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'docintel-link-connection'
        properties: {
          privateLinkServiceId: formrecognizer.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (!empty(subnetId) && !empty(dnsZoneId)) {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'docintel-dns-config'
        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

resource docintelDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${docintelName}-diagnostics'
  scope: formrecognizer
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
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

output formrecognizer_endpoint string = formrecognizer.properties.endpoint

// Note: Bicep does not have a direct equivalent to Terraform's `sensitive = true` for outputs. 
// Returning secrets via outputs means they will be visible in the deployment history. 
// For production, consider storing this directly in an Azure Key Vault within the Bicep template.
#disable-next-line outputs-should-not-contain-secrets
output formrecognizer_api_key string = formrecognizer.listKeys().key1

output formrecognizer_api_version string = docintel_api_version
