param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$spec = Join-Path $projectRoot "packaging\VaultKey.spec"
$distDir = Join-Path $projectRoot "dist\VaultKey"
$releaseDir = Join-Path $projectRoot "release"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "The project virtual environment was not found at $python"
}

Push-Location $projectRoot
try {
    $version = (& $python -c "from app.config import APP_VERSION; print(APP_VERSION)").Trim()
    if (-not $version) {
        throw "Unable to determine the VaultKey version."
    }

    if (-not $SkipTests) {
        & $python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Automated tests failed." }
    }

    & $python scripts\generate_windows_icon.py
    if ($LASTEXITCODE -ne 0) { throw "Windows icon generation failed." }

    & $python scripts\generate_windows_version_info.py $version
    if ($LASTEXITCODE -ne 0) { throw "Windows version metadata generation failed." }

    & $python -m PyInstaller --noconfirm --clean $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    $executable = Join-Path $distDir "VaultKey.exe"
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "The expected executable was not created: $executable"
    }

    foreach ($document in @("LICENSE", "NOTICE", "README.md", "THIRD_PARTY_NOTICES.txt")) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $document) -Destination $distDir -Force
    }

    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    $portable = Join-Path $releaseDir "VaultKey-Portable-$version-Windows-x64.zip"
    Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $portable -Force

    if (-not $SkipInstaller) {
        $innoCandidates = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
        )
        $iscc = $innoCandidates | Where-Object {
            $_ -and (Test-Path -LiteralPath $_ -PathType Leaf)
        } | Select-Object -First 1
        if (-not $iscc) {
            throw "Inno Setup 6 was not found. Install it or run with -SkipInstaller."
        }
        & $iscc "/DMyAppVersion=$version" "packaging\VaultKey.iss"
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
    }

    $artifacts = Get-ChildItem -LiteralPath $releaseDir -File |
        Where-Object { $_.Extension -in ".exe", ".zip" }
    foreach ($artifact in $artifacts) {
        $hash = (Get-FileHash -LiteralPath $artifact.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $checksumPath = "$($artifact.FullName).sha256"
        Set-Content -LiteralPath $checksumPath -Value "$hash *$($artifact.Name)" -Encoding ascii
    }

    Write-Host "VaultKey $version release artifacts:"
    Get-ChildItem -LiteralPath $releaseDir -File | Select-Object Name, Length
}
finally {
    Pop-Location
}
