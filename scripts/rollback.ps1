param(
    [Parameter(Mandatory = $true)][string]$Cluster,
    [Parameter(Mandatory = $true)][string]$Service,
    [Parameter(Mandatory = $true)][string]$TaskDefinition
)
$ErrorActionPreference = 'Stop'
aws ecs update-service --cluster $Cluster --service $Service --task-definition $TaskDefinition | Out-Null
aws ecs wait services-stable --cluster $Cluster --services $Service
Write-Host "Service $Service is stable on $TaskDefinition"
