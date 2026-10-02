param([string]$Python = 'python', [string]$Compiler = '.tools/inno/ISCC.exe', [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$version = (& $Python -c 'from app import __version__; print(__version__)').Trim()
& $Python -c 'import tomllib; from app import __version__; assert tomllib.load(open("pyproject.toml","rb"))["project"]["version"] == __version__'
if ($LASTEXITCODE -ne 0) { throw 'Version mismatch' }
if (-not $SkipBuild) { & (Join-Path $root 'build.ps1') -Python $Python }
$env:INTAKE_VERSION = $version
New-Item -ItemType Directory -Force -Path 'release' | Out-Null
& $Compiler /Qp 'packaging/intake.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
Compress-Archive -Path 'dist/INTAKE' -DestinationPath 'release/Intake-Portable-x64.zip' -Force
$lines = foreach ($name in @('Intake-Setup-x64.exe','Intake-Portable-x64.zip')) {
    $digest = (Get-FileHash -LiteralPath (Join-Path 'release' $name) -Algorithm SHA256).Hash.ToLower()
    "$digest  $name"
}
Set-Content -LiteralPath 'release/SHA256SUMS.txt' -Value $lines -Encoding ascii
Write-Output "INTAKE $version release artifacts are ready."
