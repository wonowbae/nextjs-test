
param(
    [Parameter(Mandatory)]
    [string]$Service,

    [Parameter(Mandatory)]
    [string]$ReleasePath
)

$ErrorActionPreference = "Stop"

$ReleasePath = (Resolve-Path $ReleasePath).Path
$xmlPath = "C:\services\$Service\service\$Service.xml"

[xml]$xml = Get-Content $xmlPath

# Stop
Stop-Service $Service
(Get-Service $Service).WaitForStatus(
    "Stopped", [TimeSpan]::FromSeconds(30)
)

# Update WinSW configuration
$xml.service.workingdirectory = $ReleasePath

if ($Service -eq "backend") {
    $xml.service.executable = "$ReleasePath\.venv\Scripts\python.exe"
}

$xml.Save($xmlPath)

# Start
Start-Service $Service
(Get-Service $Service).WaitForStatus(
    "Running", [TimeSpan]::FromSeconds(30)
)

Write-Host "Deployed $Service -> $ReleasePath"
