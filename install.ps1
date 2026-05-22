$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerPath = Join-Path $ScriptDir "server.py"
$ConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"

Write-Host "=== Installation MCP Entreprises France ===" -ForegroundColor Cyan

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $v = & $cmd --version 2>&1
        if ($v -match "Python 3") { $pythonCmd = $cmd; break }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "ERREUR : Python 3 introuvable. https://python.org" -ForegroundColor Red
    exit 1
}

Write-Host "Python OK : $(& $pythonCmd --version 2>&1)" -ForegroundColor Green
Write-Host "Installation des dependances..." -ForegroundColor Yellow
& $pythonCmd -m pip install "mcp[cli]" httpx pydantic --quiet
Write-Host "Dependances OK" -ForegroundColor Green

$pythonPath = (& $pythonCmd -c "import sys; print(sys.executable)").Trim()

if (Test-Path $ConfigPath) {
    $config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $ConfigPath) | Out-Null
    $config = [PSCustomObject]@{ mcpServers = [PSCustomObject]@{} }
}

if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([PSCustomObject]@{})
}

$newEntry = [PSCustomObject]@{ command = $pythonPath; args = @($ServerPath) }
$config.mcpServers | Add-Member -NotePropertyName "entreprises-france" -NotePropertyValue $newEntry -Force
$config | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath -Encoding UTF8

Write-Host "MCP enregistre dans : $ConfigPath" -ForegroundColor Green
Write-Host "=== TERMINE : Redemarrez Claude Desktop ===" -ForegroundColor Green
Write-Host ""
Write-Host "Outils actives :"
Write-Host "  entreprise_search"
Write-Host "  entreprise_fiche_complete"
Write-Host "  entreprise_finances"
Write-Host "  entreprise_bodacc"
Write-Host "  entreprise_dirigeants"
Write-Host "  entreprise_verifier"