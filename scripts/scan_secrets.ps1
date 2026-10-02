$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$folder = Join-Path $root '.tools/gitleaks'
New-Item -ItemType Directory -Path $folder -Force | Out-Null
$archive = Join-Path $folder 'gitleaks.zip'
Invoke-WebRequest 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_windows_x64.zip' -OutFile $archive
if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLower() -ne 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e') { throw 'Gitleaks integrity check failed' }
Expand-Archive -LiteralPath $archive -DestinationPath $folder -Force
& (Join-Path $folder 'gitleaks.exe') git . --redact --no-banner --log-opts='--all'
if ($LASTEXITCODE -ne 0) { throw 'Secret scan failed' }
