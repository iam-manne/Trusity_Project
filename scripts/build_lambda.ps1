$ErrorActionPreference = 'Stop'
$Source = Join-Path $PSScriptRoot '..\lambda_bulk_import'
$Build = Join-Path $Source 'build'
$Zip = Join-Path $Source 'bulk-import.zip'

if (Test-Path -LiteralPath $Build) { Remove-Item -LiteralPath $Build -Recurse -Force }
New-Item -ItemType Directory -Path $Build | Out-Null
python -m pip install --requirement (Join-Path $Source 'requirements.txt') --target $Build
Copy-Item -LiteralPath (Join-Path $Source 'handler.py') -Destination $Build
if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
Compress-Archive -Path (Join-Path $Build '*') -DestinationPath $Zip
Write-Host "Created $Zip"

