$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root '.tools'
New-Item -ItemType Directory -Force -Path $tools | Out-Null
$setup = Join-Path $tools 'inno-setup.exe'
Invoke-WebRequest -Uri 'https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe' -OutFile $setup
$expected = '0362a383ed217d4c4239b5933866dd96d3eb2102737da92f80f6057a4b40df2f'
if ((Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'Inno Setup digest mismatch' }
if ((Get-AuthenticodeSignature -LiteralPath $setup).Status -ne 'Valid') { throw 'Inno Setup signature is invalid' }
$destination = Join-Path $tools 'inno'
$process = Start-Process -FilePath $setup -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',('/DIR="' + $destination + '"')) -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(120000)) { throw 'Compiler setup timed out' }
if ($process.ExitCode -ne 0) { throw 'Compiler setup failed' }
Write-Output 'Verified release compiler is ready in .tools/inno.'
