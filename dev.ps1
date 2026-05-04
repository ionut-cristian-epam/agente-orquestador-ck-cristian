$root = $PSScriptRoot

# Force UTF-8 encoding in PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'UTF8'
$env:PYTHONIOENCODING = 'utf-8'

# Set NagaAI API key if not already set
if (-not $env:NAGA_API_KEY) {
    Write-Host "WARNING: NAGA_API_KEY not set. NagaAI models will not work." -ForegroundColor Yellow
    Write-Host "Set it with: `$env:NAGA_API_KEY = 'your-key-here'" -ForegroundColor Yellow
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; `$env:PYTHONIOENCODING = 'utf-8'; `$env:NAGA_API_KEY='$env:NAGA_API_KEY'; cd '$root'; python run.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 4
Start-Process "http://localhost:3000"
