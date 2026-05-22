@description('Location for all resources.')
param location string = resourceGroup().location

@description('The name of the Log Analytics Workspace')
param lawName string

resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
  }
}

output lawId string = law.id
output lawName string = law.name
