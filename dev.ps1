$root = $PSScriptRoot

# Set NagaAI API key if not already set
if (-not $env:NAGA_API_KEY) {
    Write-Host "WARNING: NAGA_API_KEY not set. NagaAI models will not work." -ForegroundColor Yellow
    Write-Host "Set it with: `$env:NAGA_API_KEY = 'your-key-here'" -ForegroundColor Yellow
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:NAGA_API_KEY='$env:NAGA_API_KEY'; cd '$root'; python run.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Start-Sleep -Seconds 4
Start-Process "http://localhost:3000"
