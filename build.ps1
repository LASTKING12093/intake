param(
    [string]$Python = "",
    [switch]$SkipRuntimeDownload
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable" }
}

if (-not $Python) {
    if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
        $Python = (Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $Python = (Get-Command python).Source
    } else {
        throw 'Python 3.12+ is required for development. Run build.ps1 -Python C:\path\to\python.exe'
    }
}
Invoke-Checked $Python @('-c', 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"')

# Always create a clean build environment; validate the deletion target first.
$workspace = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$environmentPath = [IO.Path]::GetFullPath((Join-Path $workspace '.build-venv'))
if (-not $environmentPath.StartsWith($workspace + '\') -or (Split-Path $environmentPath -Leaf) -ne '.build-venv') {
    throw 'Build environment is outside the workspace.'
}
if (Test-Path -LiteralPath $environmentPath) { Remove-Item -LiteralPath $environmentPath -Recurse -Force }
Invoke-Checked $Python @('-m', 'venv', $environmentPath)
$buildPython = Join-Path $environmentPath 'Scripts\python.exe'
Invoke-Checked $buildPython @('-m', 'pip', 'install', '-r', 'requirements-lock.txt')
if (-not $SkipRuntimeDownload) { Invoke-Checked $buildPython @('scripts\bootstrap_runtime.py') }
Invoke-Checked $buildPython @('scripts\verify_runtime.py')
Invoke-Checked $buildPython @('scripts\make_icon.py')
New-Item -ItemType Directory -Path '.test-data' -Force | Out-Null
Invoke-Checked $buildPython @('-m', 'pytest', '-q', '--basetemp=.test-data/build-tests')
$originalBuildPath = $env:PATH
try {
    # Qt uses Windows' ICU. Unrelated tools on PATH (e.g. Poppler) can have a
    # different icuuc.dll ABI that PyInstaller would otherwise collect.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\Wbem;$environmentPath\Scripts"
    Invoke-Checked $buildPython @('-m', 'PyInstaller', '--noconfirm', '--clean', 'INTAKE.spec')
} finally {
    $env:PATH = $originalBuildPath
}
Copy-Item -LiteralPath 'runtime' -Destination 'dist\INTAKE\runtime' -Recurse -Force
Copy-Item -LiteralPath 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'BUILDING.md', 'SECURITY.md', 'CHANGELOG.md' -Destination 'dist\INTAKE' -Force
New-Item -ItemType Directory -Path 'dist\INTAKE\docs' -Force | Out-Null
Copy-Item -LiteralPath 'docs\DEPENDENCY_SOURCES.md' -Destination 'dist\INTAKE\docs' -Force
if (Test-Path -LiteralPath 'VALIDATION.md') { Copy-Item -LiteralPath 'VALIDATION.md' -Destination 'dist\INTAKE' -Force }
foreach ($relative in @('INTAKE.exe', 'runtime\yt-dlp\yt-dlp.exe', 'runtime\ffmpeg\ffmpeg.exe', 'runtime\ffmpeg\ffprobe.exe', 'runtime\deno\deno.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path 'dist\INTAKE' $relative))) { throw "Missing distribution file: $relative" }
}
$previousData = $env:INTAKE_DATA_DIR
try {
    $env:INTAKE_DATA_DIR = Join-Path $workspace '.test-data\build-smoke'
    $smokeResult = Join-Path $env:INTAKE_DATA_DIR 'smoke\result.txt'
    if (Test-Path -LiteralPath $smokeResult) { Remove-Item -LiteralPath $smokeResult -Force }
    $process = Start-Process -FilePath (Join-Path $workspace 'dist\INTAKE\INTAKE.exe') -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Packaged startup test timed out.' }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $smokeResult)) { throw 'Packaged startup test failed.' }
} finally {
    $env:INTAKE_DATA_DIR = $previousData
}
Compress-Archive -Path 'dist\INTAKE' -DestinationPath 'dist\INTAKE-Windows-x64.zip' -Force
Write-Host 'Build verified: dist\INTAKE\INTAKE.exe' -ForegroundColor Green
Write-Host 'Portable distribution: dist\INTAKE-Windows-x64.zip'
