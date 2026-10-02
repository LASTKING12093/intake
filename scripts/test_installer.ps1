param([string]$Installer = 'release/Intake-Setup-x64.exe')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$isolated = [IO.Path]::GetFullPath((Join-Path $root '.test-data/installer'))
if (-not $isolated.StartsWith([IO.Path]::GetFullPath($root).TrimEnd('\') + '\')) { throw 'Unsafe test directory' }
New-Item -ItemType Directory -Force -Path $isolated | Out-Null
$appDir = Join-Path $isolated 'application'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B78C267D-EB7A-4DF1-B80B-295417FA01E3}_is1'
if (Test-Path -LiteralPath $uninstallKey) { throw 'An existing INTAKE installation is registered; use a clean test account.' }
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'INTAKE\INTAKE.lnk'
if (Test-Path -LiteralPath $shortcut) { throw 'An existing INTAKE shortcut must not be overwritten by this test.' }
$media = Join-Path $isolated 'user-media.txt'
Set-Content -LiteralPath $media -Value 'This user file must survive uninstall.'
$install = Start-Process -FilePath (Join-Path $root $Installer) -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="' + $appDir + '"')) -WindowStyle Hidden -PassThru
if (-not $install.WaitForExit(120000) -or $install.ExitCode -ne 0) { throw 'Installation failed' }
if (-not (Test-Path -LiteralPath $uninstallKey)) { throw 'Uninstall registration was not created' }
if (-not (Test-Path -LiteralPath $shortcut)) { throw 'Start Menu shortcut was not created' }
$entry = Get-ItemProperty -LiteralPath $uninstallKey
if ($entry.DisplayName -notlike 'INTAKE*' -or $entry.DisplayIcon -notlike '*INTAKE.exe*') { throw 'Invalid uninstall identity/icon' }
foreach ($file in @('INTAKE.exe','runtime/ffmpeg/ffmpeg.exe','runtime/ffmpeg/ffprobe.exe','runtime/yt-dlp/yt-dlp.exe','runtime/deno/deno.exe','unins000.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $appDir $file))) { throw "Missing installed file: $file" }
}
$distribution = Join-Path $root 'dist/INTAKE'
foreach ($original in Get-ChildItem -LiteralPath $distribution -Recurse -File) {
    $relative = [IO.Path]::GetRelativePath($distribution, $original.FullName)
    $installed = Join-Path $appDir $relative
    if (-not (Test-Path -LiteralPath $installed) -or (Get-FileHash -LiteralPath $original.FullName).Hash -ne (Get-FileHash -LiteralPath $installed).Hash) {
        throw "Installed file differs from audited distribution: $relative"
    }
}
$previous = $env:INTAKE_DATA_DIR
try {
    $env:INTAKE_DATA_DIR = Join-Path $isolated 'profile'
    $app = Start-Process -FilePath (Join-Path $appDir 'INTAKE.exe') -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
    if (-not $app.WaitForExit(60000) -or $app.ExitCode -ne 0) { throw 'Installed application smoke test failed' }
    if (-not (Test-Path -LiteralPath (Join-Path $env:INTAKE_DATA_DIR 'smoke/result.txt'))) { throw 'Missing download evidence' }
} finally { $env:INTAKE_DATA_DIR = $previous }
$uninstall = Start-Process -FilePath (Join-Path $appDir 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -PassThru
if (-not $uninstall.WaitForExit(120000) -or $uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath (Join-Path $appDir 'INTAKE.exe')) { throw 'Application executable remained after uninstall' }
if (Test-Path -LiteralPath $uninstallKey) { throw 'Uninstall registration remained after uninstall' }
if (Test-Path -LiteralPath $shortcut) { throw 'Start Menu shortcut remained after uninstall' }
if (-not (Test-Path -LiteralPath $media)) { throw 'Uninstall removed user media' }
if (-not (Test-Path -LiteralPath (Join-Path $isolated 'profile/smoke/result.txt'))) { throw 'Uninstall removed user data' }
Write-Output 'Installer, installed downloads, uninstaller and preserved user data verified.'
