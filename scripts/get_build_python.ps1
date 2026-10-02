$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $root '.tools'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$archive = Join-Path $destination 'python.tar.gz'
$url = 'https://github.com/astral-sh/python-build-standalone/releases/download/20260929/cpython-3.12.14%2B20260929-x86_64-pc-windows-msvc-install_only_stripped.tar.gz'
Invoke-WebRequest -Uri $url -OutFile $archive
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne 'f38e68f4d612ade6dd50c894fc80b14c0be0c3b5201145d6fff5f20b9323204d') { throw 'Python archive integrity check failed' }
& tar -xzf $archive -C $destination
if ($LASTEXITCODE -ne 0) { throw 'Python archive extraction failed' }
$python = Join-Path $destination 'python/python.exe'
& $python -c 'import sys; assert sys.version_info[:3] == (3,12,14)'
if ($LASTEXITCODE -ne 0) { throw 'Python version check failed' }
Write-Output 'Verified Python 3.12.14 is ready in .tools/python.'
