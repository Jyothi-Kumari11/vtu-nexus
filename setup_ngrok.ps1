# PowerShell Script to automatically download and setup Ngrok for VTU Nexus
$ErrorActionPreference = "Stop"

Write-Host "[i] Downloading stable Windows x64 binary for Ngrok..." -ForegroundColor Cyan
$downloadUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$zipPath = Join-Path $PSScriptRoot "ngrok.zip"
$destFolder = $PSScriptRoot

# Download zip file
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath

Write-Host "[-] Extracting ngrok.exe to project folder..." -ForegroundColor Cyan
Expand-Archive -Path $zipPath -DestinationPath $destFolder -Force

# Clean up zip
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# Verify installation
$exePath = Join-Path $destFolder "ngrok.exe"
if (Test-Path $exePath) {
    Write-Host "[OK] Ngrok has been successfully downloaded and placed in your project directory!" -ForegroundColor Green
    Write-Host "Version Details:" -ForegroundColor Yellow
    & $exePath --version
} else {
    Write-Error "[ERROR] Extraction failed! ngrok.exe was not found."
}
