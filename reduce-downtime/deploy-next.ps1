
param(
    [Parameter(Mandatory = $true)]
    [string]$ReleasePath,

    [string]$ServiceName = "frontend",

    [string]$XmlPath =
        "C:\services\frontend\service\frontend.xml",

    [string]$HealthUrl =
        "http://127.0.0.1:3000/api/health",

    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceTimeout = 30
$HealthRetries = 20
$HealthInterval = 2

$ReleaseRoot = "C:\services\frontend\releases"
$BackupDir = Join-Path (Split-Path $XmlPath) "backups"

# Deployment state
$ConfigChanged = $false
$DeploymentSucceeded = $false
$BackupPath = $null

function Write-Log {
    param([string]$Message)

    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$time] $Message"
}

function Wait-ServiceState {
    param(
        [string]$State
    )

    $service = Get-Service -Name $ServiceName

    $service.WaitForStatus(
        $State,
        [TimeSpan]::FromSeconds($ServiceTimeout)
    )
}

function Wait-PortReleased {
    # Prevent starting a new server while an old process
    # still owns the listening port.

    for ($i = 0; $i -lt 30; $i++) {
        $listeners = Get-NetTCPConnection `
            -LocalPort $Port `
            -State Listen `
            -ErrorAction SilentlyContinue

        if (!$listeners) {
            return
        }

        Start-Sleep -Seconds 1
    }

    throw "Port $Port is still occupied"
}

function Test-ApplicationHealth {
    for ($i = 1; $i -le $HealthRetries; $i++) {
        try {
            $response = Invoke-WebRequest `
                -Uri $HealthUrl `
                -UseBasicParsing `
                -TimeoutSec 3

            if ($response.StatusCode -eq 200) {
                Write-Log "Health check passed"
                return $true
            }
        }
        catch {
            Write-Log "Health attempt $i failed"
        }

        Start-Sleep -Seconds $HealthInterval
    }

    return $false
}

function Stop-AppService {
    Write-Log "Stopping service: $ServiceName"

    $service = Get-Service -Name $ServiceName

    if ($service.Status -ne "Stopped") {
        Stop-Service -Name $ServiceName -ErrorAction Stop
        Wait-ServiceState "Stopped"
    }

    Wait-PortReleased

    Write-Log "Service stopped and port released"
}

function Start-AppService {
    Write-Log "Starting service: $ServiceName"

    Start-Service -Name $ServiceName -ErrorAction Stop

    Wait-ServiceState "Running"

    if (!(Test-ApplicationHealth)) {
        throw "Application health check failed"
    }

    Write-Log "Service started successfully"
}

function Replace-Config {
    param(
        [string]$SourcePath
    )

    # Atomic replacement on the same NTFS volume.
    $tempPath = "$XmlPath.$([guid]::NewGuid().ToString('N')).tmp"

    try {
        Copy-Item $SourcePath $tempPath -Force
        [System.IO.File]::Replace(
            $tempPath,
            $XmlPath,
            $null
        )
    }
    finally {
        if (Test-Path $tempPath) {
            Remove-Item $tempPath -Force
        }
    }
}

# ===================================================
# 1. Preflight validation (no downtime)
# ===================================================

Write-Log "Starting deployment"

$ReleasePath = (Resolve-Path $ReleasePath).Path
$ReleaseRoot = (Resolve-Path $ReleaseRoot).Path

$rootPrefix = $ReleaseRoot.TrimEnd('\') + '\'

if (!$ReleasePath.StartsWith(
    $rootPrefix,
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "Release must be inside $ReleaseRoot"
}

if (!(Test-Path "$ReleasePath\server.js" -PathType Leaf)) {
    throw "server.js does not exist"
}

if (!(Test-Path "$ReleasePath\.next\static" -PathType Container)) {
    throw "Next.js static assets are missing"
}

if (!(Test-Path $XmlPath -PathType Leaf)) {
    throw "WinSW XML does not exist: $XmlPath"
}

$service = Get-Service -Name $ServiceName -ErrorAction Stop

if ($service.Status -ne "Running") {
    throw "Expected running service, got: $($service.Status)"
}

# Parse and validate existing XML
[xml]$xml = Get-Content $XmlPath

if (!$xml.service.workingdirectory) {
    throw "WinSW XML has no workingdirectory element"
}

if ($xml.service.arguments.Trim() -ne "server.js") {
    throw "Expected WinSW arguments: server.js"
}

# Backup configuration before stopping the service
New-Item -ItemType Directory `
    -Path $BackupDir -Force | Out-Null

$backupName = "frontend-$([guid]::NewGuid().ToString('N')).xml"
$BackupPath = Join-Path $BackupDir $backupName

Copy-Item $XmlPath $BackupPath

# Prepare new XML while the old server is running
$xml.service.workingdirectory = $ReleasePath

$tempConfig = Join-Path $BackupDir `
    "prepared-$([guid]::NewGuid().ToString('N')).xml"

$xml.Save($tempConfig)

Write-Log "Release: $ReleasePath"
Write-Log "XML backup: $BackupPath"
Write-Log "Preflight completed"

# ===================================================
# 2. Deployment (downtime starts here)
# ===================================================

try {
    Stop-AppService

    # Switch configuration only after the service stops
    Replace-Config -SourcePath $tempConfig
    $ConfigChanged = $true

    Start-AppService

    $DeploymentSucceeded = $true
    Write-Log "DEPLOYMENT SUCCESS"
}

catch {
    $deploymentError = $_.Exception.Message
    Write-Log "DEPLOYMENT FAILED: $deploymentError"

    try {
        # Restore the original service configuration if changed
        if ($ConfigChanged) {
            Write-Log "Rolling back configuration"

            Stop-AppService
            Replace-Config -SourcePath $BackupPath
        }

        # If the old service is stopped, restart it
        $service = Get-Service -Name $ServiceName

        if ($service.Status -ne "Running") {
            Wait-PortReleased
            Start-AppService
        }
        elseif (!(Test-ApplicationHealth)) {
            throw "Original service is running but unhealthy"
        }

        Write-Log "ROLLBACK SUCCESS"
    }
    catch {
        $rollbackError = $_.Exception.Message
        throw "Deployment failed: $deploymentError; Rollback failed: $rollbackError"
    }

    throw "Deployment failed and rolled back: $deploymentError"
}

finally {
    if (Test-Path $tempConfig) {
        Remove-Item $tempConfig -Force
    }
}

if (!$DeploymentSucceeded) {
    throw "Deployment did not complete"
}

Write-Log "Deployment finished"
