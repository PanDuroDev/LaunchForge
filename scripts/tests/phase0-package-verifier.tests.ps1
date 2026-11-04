$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$verifier = Join-Path $PSScriptRoot "..\verify-phase0-portable.ps1"
$work = Join-Path ([IO.Path]::GetTempPath()) ("LaunchForge-Verifier-Tests-" + [Guid]::NewGuid().ToString("N"))
[void] [IO.Directory]::CreateDirectory($work)

function New-TestPackage {
    param(
        [Parameter(Mandatory = $true)][string] $ZipPath,
        [bool] $IncludeLockfile = $true,
        [bool] $ValidIconReference = $true,
        [bool] $ValidManifestDigest = $true,
        [string] $AssetPath = "assets/-sample-cover-.svg",
        [bool] $IncludeNestedNativeBinary = $false
    )

    $folder = Join-Path (Split-Path -Parent $ZipPath) ([IO.Path]::GetFileNameWithoutExtension($ZipPath))
    [void] [IO.Directory]::CreateDirectory($folder)

    [IO.File]::WriteAllText((Join-Path $folder "launchforge_phase0_spike.exe"), "MZ-test-placeholder-not-executed")
    if ($IncludeNestedNativeBinary) {
        $nestedFolder = Join-Path $folder "nested"
        [void] [IO.Directory]::CreateDirectory($nestedFolder)
        [IO.File]::WriteAllText((Join-Path $nestedFolder "launchforge_phase0_spike.exe"), "MZ-unexpected-nested-binary")
    }
    if ($IncludeLockfile) {
        [IO.File]::WriteAllText((Join-Path $folder "Cargo.lock"), "# generated fixture lockfile")
    }

    $assetHash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    $iconHash = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    $iconId = if ($ValidIconReference) { "11111111-1111-4111-8111-111111111111" } else { "99999999-9999-4999-8999-999999999999" }

    $manifest = @(
        [ordered]@{
            id = "11111111-1111-4111-8111-111111111111"
            kind = "applicationIcon"
            path = "assets/launcher-icon.ico"
            sha256 = $iconHash
        },
        [ordered]@{
            id = "22222222-2222-4222-8222-222222222222"
            kind = "image"
            path = $AssetPath
            sha256 = $assetHash
        }
    )
    $canonicalManifest = '[{"id":"11111111-1111-4111-8111-111111111111","kind":"applicationIcon","path":"assets/launcher-icon.ico","sha256":"' +
        $iconHash + '"},{"id":"22222222-2222-4222-8222-222222222222","kind":"image","path":"' + $AssetPath + '","sha256":"' +
        $assetHash + '"}]'
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $manifestDigest = [BitConverter]::ToString(
            $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonicalManifest))
        ).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
    }
    if (-not $ValidManifestDigest) {
        $manifestDigest = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    }

    $metadata = [ordered]@{
        format = "launchforge.export"
        buildContractVersion = 1
        projectSchemaVersion = 1
        renderer = "shared-dom-v1"
        assetManifest = $manifest
        assetManifestSha256 = $manifestDigest
        applicationIconAssetId = $iconId
        applicationIconSha256 = $iconHash
    }

    $metadataJson = ConvertTo-Json -InputObject $metadata -Depth 8
    [IO.File]::WriteAllText((Join-Path $folder "BUILD-METADATA.json"), $metadataJson)
    if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
    Compress-Archive -Path (Join-Path $folder "*") -DestinationPath $ZipPath -Force
}

function Invoke-Verifier {
    param([string] $ZipPath, [string] $ReportPath)

    $pwsh = Join-Path $PSHOME "pwsh.exe"
    $output = & $pwsh -NoLogo -NoProfile -File $verifier -PackageZip $ZipPath -OutputPath $ReportPath -ValidateOnly 2>&1
    $exitCode = $LASTEXITCODE
    $report = if (Test-Path -LiteralPath $ReportPath) {
        Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
    } else {
        $null
    }
    return [pscustomobject]@{
        exitCode = $exitCode
        output = ($output | Out-String)
        report = $report
    }
}

function Assert-True {
    param([bool] $Condition, [string] $Message)
    if (-not $Condition) { throw $Message }
}

try {
    $validZip = Join-Path $work "valid.zip"
    $validReport = Join-Path $work "valid-report.json"
    New-TestPackage -ZipPath $validZip
    $valid = Invoke-Verifier -ZipPath $validZip -ReportPath $validReport
    Assert-True ($valid.exitCode -eq 0) ("Valid package was rejected: " + $valid.output)
    Assert-True ($valid.report.status -eq "passed") "Valid package report did not record passed."
    Assert-True ($valid.report.checks.archiveSafety -eq "passed") "Archive safety check did not pass."
    Assert-True ($valid.report.checks.buildMetadata -eq "passed") "Build metadata check did not pass."
    Write-Host "PASS: valid package and metadata are accepted."

    $missingLockZip = Join-Path $work "missing-lock.zip"
    $missingLockReport = Join-Path $work "missing-lock-report.json"
    New-TestPackage -ZipPath $missingLockZip -IncludeLockfile $false
    $missingLock = Invoke-Verifier -ZipPath $missingLockZip -ReportPath $missingLockReport
    Assert-True ($missingLock.exitCode -ne 0) "A package without Cargo.lock was accepted."
    Assert-True ($missingLock.report.status -eq "failed") "Missing-lockfile failure was not written to the report."
    Assert-True ($missingLock.report.failure -match "Cargo.lock") "The missing-lockfile fixture failed for an unexpected reason."
    Write-Host "PASS: package without the reviewed Cargo.lock is rejected."

    $badIconZip = Join-Path $work "bad-icon.zip"
    $badIconReport = Join-Path $work "bad-icon-report.json"
    New-TestPackage -ZipPath $badIconZip -ValidIconReference $false
    $badIcon = Invoke-Verifier -ZipPath $badIconZip -ReportPath $badIconReport
    Assert-True ($badIcon.exitCode -ne 0) "A package with a dangling application-icon reference was accepted."
    Assert-True ($badIcon.report.failure -match "application icon reference") "The dangling-icon fixture failed for an unexpected reason."
    Write-Host "PASS: dangling application-icon references are rejected."

    $nestedBinaryZip = Join-Path $work "nested-binary.zip"
    $nestedBinaryReport = Join-Path $work "nested-binary-report.json"
    New-TestPackage -ZipPath $nestedBinaryZip -IncludeNestedNativeBinary $true
    $nestedBinary = Invoke-Verifier -ZipPath $nestedBinaryZip -ReportPath $nestedBinaryReport
    Assert-True ($nestedBinary.exitCode -ne 0) "A package with an extra nested native binary was accepted."
    Assert-True ($nestedBinary.report.failure -match "additional native binaries") "The nested-binary fixture failed for an unexpected reason."
    Write-Host "PASS: additional nested native binaries are rejected."

    $badManifestZip = Join-Path $work "bad-manifest.zip"
    $badManifestReport = Join-Path $work "bad-manifest-report.json"
    New-TestPackage -ZipPath $badManifestZip -ValidManifestDigest $false
    $badManifest = Invoke-Verifier -ZipPath $badManifestZip -ReportPath $badManifestReport
    Assert-True ($badManifest.exitCode -ne 0) "A package with an incorrect asset-manifest digest was accepted."
    Assert-True ($badManifest.report.failure -match "assetManifestSha256") "The bad manifest digest was rejected for an unexpected reason."
    Write-Host "PASS: incorrect canonical asset-manifest digests are rejected."

    $unsafeAssetPathZip = Join-Path $work "unsafe-asset-path.zip"
    $unsafeAssetPathReport = Join-Path $work "unsafe-asset-path-report.json"
    New-TestPackage -ZipPath $unsafeAssetPathZip -AssetPath "assets/../outside.svg"
    $unsafeAssetPath = Invoke-Verifier -ZipPath $unsafeAssetPathZip -ReportPath $unsafeAssetPathReport
    Assert-True ($unsafeAssetPath.exitCode -ne 0) "A package with a non-portable asset path was accepted."
    Assert-True ($unsafeAssetPath.report.failure -match "non-portable") "The unsafe asset path was rejected for an unexpected reason."
    Write-Host "PASS: non-portable asset paths are rejected."

    $traversalZip = Join-Path $work "traversal.zip"
    $stream = [IO.File]::Open($traversalZip, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create)
    try {
        $entry = $zip.CreateEntry("../outside.txt")
        $entryStream = $entry.Open()
        $bytes = [Text.Encoding]::UTF8.GetBytes("outside")
        $entryStream.Write($bytes, 0, $bytes.Length)
        $entryStream.Dispose()
    }
    finally {
        $zip.Dispose()
    }

    $traversalReport = Join-Path $work "traversal-report.json"
    $traversal = Invoke-Verifier -ZipPath $traversalZip -ReportPath $traversalReport
    Assert-True ($traversal.exitCode -ne 0) "A ZIP traversal entry was accepted."
    Assert-True ($traversal.report.failure -match "traversal|invalid entry path|absolute") "Traversal rejection did not report the unsafe entry."
    Write-Host "PASS: ZIP traversal entries are rejected."

    Write-Host "All Phase 0 package-verifier tests passed."
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

# Expected negative fixtures set LASTEXITCODE to 1; all assertions above determine the test result.
exit 0
