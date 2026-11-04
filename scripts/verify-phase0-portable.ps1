[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string] $PackageZip,
    [string] $OutputPath = "phase0-clean-machine-report.json",
    [ValidateRange(5, 120)]
    [int] $WindowTimeoutSeconds = 60,
    [ValidateRange(1, 300)]
    [int] $SmokeSeconds = 10,
    [switch] $ValidateOnly
)

$ErrorActionPreference = "Stop"
$report = [ordered]@{
    reportVersion = 1
    status = "running"
    mode = if ($ValidateOnly) { "archive-only" } else { "clean-machine-launch" }
    startedAtUtc = [DateTime]::UtcNow.ToString("o")
    checks = [ordered]@{
        windowsX64 = "not-run"
        archiveSafety = "not-run"
        packageContents = "not-run"
        buildMetadata = "not-run"
        standardUser = "not-run"
        webView2Runtime = "not-run"
        applicationWindow = "not-run"
        processLifetime = "not-run"
    }
    limitations = @(
        "StartupToWindowHandleMs is not first-usable-frame latency.",
        "This script does not prove visual parity, accessibility, keyboard behavior, RTL, or DPI scaling.",
        "A successful run applies only to the recorded machine and package."
    )
}

$archive = $null
$extractRoot = $null
$process = $null

function Get-ProcessTreeIds {
    param([int] $RootPid, [object[]] $Snapshot)
    $ids = New-Object 'System.Collections.Generic.HashSet[int]'
    [void] $ids.Add($RootPid)
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($item in $Snapshot) {
            $candidateId = [int] $item.ProcessId
            $parentId = [int] $item.ParentProcessId
            if (-not $ids.Contains($candidateId) -and $ids.Contains($parentId)) {
                [void] $ids.Add($candidateId)
                $changed = $true
            }
        }
    }
    return @($ids)
}

function Get-WebView2Installations {
    $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    $roots = @(
        $(if ($programFilesX86) { Join-Path $programFilesX86 "Microsoft\EdgeWebView\Application" }),
        $(if ($env:ProgramFiles) { Join-Path $env:ProgramFiles "Microsoft\EdgeWebView\Application" }),
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Microsoft\EdgeWebView\Application" })
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) }

    $found = @()
    foreach ($root in $roots) {
        foreach ($versionDirectory in Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue) {
            if ($versionDirectory.Name -match '^\d+\.\d+\.\d+\.\d+$') {
                $runtimePath = Join-Path $versionDirectory.FullName "msedgewebview2.exe"
                if (Test-Path -LiteralPath $runtimePath -PathType Leaf) {
                    $found += [pscustomobject]@{ version = $versionDirectory.Name; executable = $runtimePath }
                }
            }
        }
    }
    return @($found | Sort-Object version -Unique)
}

function Test-Sha256 {
    param([string] $Value)
    return ($Value -match '^[0-9a-fA-F]{64}$')
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "This verifier must run on Windows."
    }
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw "The Phase 0 package target is Windows x64; this machine is not 64-bit."
    }
    $report.checks.windowsX64 = "passed"

    if (-not $ValidateOnly) {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        $adminSid = [Security.Principal.SecurityIdentifier]::new([Security.Principal.WellKnownSidType]::BuiltinAdministratorsSid, $null)
        $isAdminMember = @($identity.Groups | ForEach-Object { $_.Value }) -contains $adminSid.Value
        $isElevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or $isAdminMember
        if ($isElevated) {
            throw "Run this check from a standard user account that is not a member of Administrators."
        }
        $report.checks.standardUser = "passed"
    }

    $zipPath = (Resolve-Path -LiteralPath $PackageZip).Path
    $zipInfo = Get-Item -LiteralPath $zipPath
    if ($zipInfo.Length -le 0) { throw "The package ZIP is empty." }

    $report.package = [ordered]@{
        fileName = $zipInfo.Name
        compressedBytes = [long] $zipInfo.Length
        sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    if ($archive.Entries.Count -lt 1 -or $archive.Entries.Count -gt 100) {
        throw "The ZIP must contain between 1 and 100 entries."
    }

    $extractRoot = Join-Path ([IO.Path]::GetTempPath()) ("LaunchForge-Phase0-" + [Guid]::NewGuid().ToString("N"))
    [void] [IO.Directory]::CreateDirectory($extractRoot)
    $rootPrefix = [IO.Path]::GetFullPath($extractRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    [long] $expandedBytes = 0

    foreach ($entry in $archive.Entries) {
        $entryName = $entry.FullName
        if ([string]::IsNullOrWhiteSpace($entryName) -or $entryName.Contains("\")) {
            throw "The ZIP contains an empty or non-portable entry path."
        }
        $isDirectory = $entryName.EndsWith("/")
        $portableName = $entryName.TrimEnd("/")
        if ([string]::IsNullOrWhiteSpace($portableName) -or $portableName.StartsWith("/") -or $portableName -match '^[a-zA-Z]:') {
            throw "The ZIP contains an absolute or invalid entry path: $entryName"
        }

        $segments = @($portableName.Split("/"))
        $badSegments = @($segments | Where-Object {
            $_ -eq ".." -or $_ -eq "." -or $_ -eq "" -or
            $_.EndsWith(".") -or $_.EndsWith(" ") -or
            $_ -match '[:*?"<>|]' -or
            $_ -match '^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$'
        })
        if ($badSegments.Count -gt 0) {
            throw "The ZIP contains a traversal or non-portable Windows path: $entryName"
        }

        $unixType = ([int] $entry.ExternalAttributes -shr 16) -band 0xF000
        if ($unixType -eq 0xA000) { throw "The ZIP contains a symbolic link: $entryName" }

        $declaredEntryLength = [long] $entry.Length
        if ($declaredEntryLength -gt 536870912 -or
            ($expandedBytes + $declaredEntryLength) -gt 536870912) {
            throw "The ZIP declares content beyond the 512 MiB safety limit."
        }

        $relativePath = $portableName.Replace("/", [IO.Path]::DirectorySeparatorChar)
        $destination = [IO.Path]::GetFullPath([IO.Path]::Combine($extractRoot, $relativePath))
        if (-not $destination.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "The ZIP entry escapes the extraction directory: $entryName"
        }

        if ($isDirectory) {
            [void] [IO.Directory]::CreateDirectory($destination)
            continue
        }

        [void] [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))
        $inputStream = $entry.Open()
        $outputStream = [IO.File]::Open($destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        [long] $entryBytesWritten = 0
        $buffer = New-Object byte[] 65536
        try {
            while (($bytesRead = $inputStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $entryBytesWritten += $bytesRead
                $expandedBytes += $bytesRead
                if ($expandedBytes -gt 536870912) {
                    throw "The ZIP expands beyond the 512 MiB safety limit while extracting."
                }
                if ($entryBytesWritten -gt [long] $entry.Length) {
                    throw "The extracted entry exceeds its declared ZIP length: $entryName"
                }
                $outputStream.Write($buffer, 0, $bytesRead)
            }
            if ($entryBytesWritten -ne [long] $entry.Length) {
                throw "The extracted entry length does not match its ZIP metadata: $entryName"
            }
        }
        finally {
            $outputStream.Dispose()
            $inputStream.Dispose()
        }
    }

    $archive.Dispose()
    $archive = $null
    $report.checks.archiveSafety = "passed"
    $report.package.expandedBytes = $expandedBytes

    $executableName = "launchforge_phase0_spike.exe"
    $executablePath = Join-Path $extractRoot $executableName
    $metadataPath = Join-Path $extractRoot "BUILD-METADATA.json"
    $lockfilePath = Join-Path $extractRoot "Cargo.lock"

    foreach ($requiredPath in @($executablePath, $metadataPath, $lockfilePath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required package file is missing: $([IO.Path]::GetFileName($requiredPath))"
        }
        if ((Get-Item -LiteralPath $requiredPath).Length -le 0) {
            throw "Required package file is empty: $([IO.Path]::GetFileName($requiredPath))"
        }
    }

    $packageFiles = @(Get-ChildItem -LiteralPath $extractRoot -File -Recurse -Force)
    $unexpectedNativeFiles = @($packageFiles | Where-Object {
        $_.Extension -match '^\.(exe|dll|node)$' -and $_.FullName -ine $executablePath
    })
    if ($unexpectedNativeFiles.Count -gt 0) {
        throw "Unexpected additional native binaries: $($unexpectedNativeFiles.Name -join ', ')"
    }
    $report.package.fileCount = $packageFiles.Count
    $report.package.executableSha256 = (Get-FileHash -LiteralPath $executablePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.checks.packageContents = "passed"

    $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
    if ($metadata.format -ne "launchforge.export" -or [int] $metadata.buildContractVersion -ne 1 -or
        [int] $metadata.projectSchemaVersion -ne 1 -or [string]::IsNullOrWhiteSpace([string] $metadata.renderer)) {
        throw "BUILD-METADATA.json does not describe a supported LaunchForge v1 export."
    }
    if (-not (Test-Sha256 ([string] $metadata.assetManifestSha256)) -or
        -not (Test-Sha256 ([string] $metadata.applicationIconSha256)) -or
        [string]::IsNullOrWhiteSpace([string] $metadata.applicationIconAssetId)) {
        throw "Build metadata is missing a valid asset-manifest or application-icon digest."
    }

    $manifest = @($metadata.assetManifest)
    if ($manifest.Count -lt 1) { throw "Build metadata contains no declared asset manifest." }
    $assetIds = @($manifest | ForEach-Object { [string] $_.id })
    if (@($assetIds | Select-Object -Unique).Count -ne $assetIds.Count) {
        throw "The asset manifest contains duplicate asset IDs."
    }
    $assetPathKeys = @($manifest | ForEach-Object { ([string] $_.path).ToLowerInvariant() })
    if (@($assetPathKeys | Select-Object -Unique).Count -ne $assetPathKeys.Count) {
        throw "The asset manifest contains duplicate paths using Windows case-insensitive comparison."
    }

    $sortedAssetIds = [string[]] @($assetIds)
    [Array]::Sort($sortedAssetIds, [StringComparer]::Ordinal)
    if (($sortedAssetIds -join "|") -cne ($assetIds -join "|")) {
        throw "The asset manifest must be sorted by stable asset ID."
    }

    $canonicalEntries = @(
        foreach ($asset in $manifest) {
            $assetId = [string] $asset.id
            $assetKind = [string] $asset.kind
            $assetPath = [string] $asset.path
            $assetHash = [string] $asset.sha256
            $parsedId = [Guid]::Empty
            if ($assetId -cne $assetId.ToLowerInvariant() -or
                -not [Guid]::TryParseExact($assetId, "D", [ref] $parsedId) -or
                $assetId.Substring(14, 1) -ne "4" -or
                $assetId.Substring(19, 1) -notin @("8", "9", "a", "b") -or
                $assetKind -notin @("image", "applicationIcon") -or
                -not (Test-Sha256 $assetHash)) {
                throw "The asset manifest contains an invalid ID, kind, or SHA-256 value."
            }

            if (-not $assetPath.StartsWith("assets/", [StringComparison]::Ordinal) -or
                $assetPath.Length -le 7 -or
                $assetPath.Contains("\") -or
                $assetPath.Contains(":") -or
                $assetPath.EndsWith(".") -or
                $assetPath.EndsWith(" ")) {
                throw "The asset manifest contains a non-portable project asset path."
            }
            $assetFileName = $assetPath.Substring(7)
            $hasInvalidFilenameCharacter = $assetFileName.Length -gt 120
            foreach ($character in $assetFileName.ToCharArray()) {
                $characterCode = [int] $character
                $isAllowedCharacter = ($characterCode -ge 48 -and $characterCode -le 57) -or
                    ($characterCode -ge 65 -and $characterCode -le 90) -or
                    ($characterCode -ge 97 -and $characterCode -le 122) -or
                    $characterCode -eq 45 -or $characterCode -eq 46 -or $characterCode -eq 95
                if (-not $isAllowedCharacter) {
                    $hasInvalidFilenameCharacter = $true
                    break
                }
            }
            $firstCharacterCode = [int] $assetFileName[0]
            $lastCharacterCode = [int] $assetFileName[$assetFileName.Length - 1]
            $firstIsAlphanumeric = ($firstCharacterCode -ge 48 -and $firstCharacterCode -le 57) -or
                ($firstCharacterCode -ge 65 -and $firstCharacterCode -le 90) -or
                ($firstCharacterCode -ge 97 -and $firstCharacterCode -le 122)
            $lastIsPortable = $lastCharacterCode -eq 45 -or $lastCharacterCode -eq 95 -or
                ($lastCharacterCode -ge 48 -and $lastCharacterCode -le 57) -or
                ($lastCharacterCode -ge 65 -and $lastCharacterCode -le 90) -or
                ($lastCharacterCode -ge 97 -and $lastCharacterCode -le 122)
            if ($hasInvalidFilenameCharacter -or -not $firstIsAlphanumeric -or -not $lastIsPortable) {
                throw "The asset manifest contains a non-portable Windows filename."
            }
            $assetStem = $assetFileName.Split(".")[0].ToUpperInvariant()
            if ($assetStem -in @("CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9")) {
                throw "The asset manifest contains a reserved Windows device filename."
            }
            if ($assetKind -eq "applicationIcon" -and -not $assetPath.EndsWith(".ico", [StringComparison]::Ordinal)) {
                throw "An applicationIcon asset must use a lowercase .ico path."
            }
            if ($assetKind -eq "image" -and $assetPath.EndsWith(".ico", [StringComparison]::OrdinalIgnoreCase)) {
                throw "An ICO asset must be classified as applicationIcon."
            }

            $canonicalEntry = [ordered]@{
                id = $assetId
                kind = $assetKind
                path = $assetPath
                sha256 = $assetHash
            }
            ConvertTo-Json -InputObject $canonicalEntry -Compress -Depth 4
        }
    )
    $canonicalManifest = "[" + ($canonicalEntries -join ",") + "]"
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $computedManifestHash = [BitConverter]::ToString(
            $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonicalManifest))
        ).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
    }
    if ($computedManifestHash -cne ([string] $metadata.assetManifestSha256).ToLowerInvariant()) {
        throw "The declared assetManifestSha256 does not match the canonical asset manifest."
    }
    $iconEntries = @($manifest | Where-Object {
        $_.id -eq $metadata.applicationIconAssetId -and $_.kind -eq "applicationIcon"
    })
    if ($iconEntries.Count -ne 1 -or $iconEntries[0].sha256 -ne $metadata.applicationIconSha256) {
        throw "The application icon reference does not resolve to one matching applicationIcon manifest entry."
    }

    $report.build = [ordered]@{
        projectSchemaVersion = [int] $metadata.projectSchemaVersion
        renderer = [string] $metadata.renderer
        assetCount = $manifest.Count
        assetManifestSha256 = [string] $metadata.assetManifestSha256
        applicationIconAssetId = [string] $metadata.applicationIconAssetId
        applicationIconSha256 = [string] $metadata.applicationIconSha256
    }
    $report.checks.buildMetadata = "passed"

    if ($ValidateOnly) {
        $report.checks.standardUser = "not-run"
        $report.checks.webView2Runtime = "not-run"
        $report.checks.applicationWindow = "not-run"
        $report.checks.processLifetime = "not-run"
    }
    else {
        $os = Get-CimInstance Win32_OperatingSystem
        $report.environment = [ordered]@{
            os = $os.Caption
            osVersion = $os.Version
            architecture = $env:PROCESSOR_ARCHITECTURE
            cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)
            logicalProcessors = [Environment]::ProcessorCount
            totalMemoryMB = [Math]::Round($os.TotalVisibleMemorySize / 1024, 0)
            standardUser = $true
            developerToolsPresent = @("node", "npm", "rustc", "cargo", "dotnet") | Where-Object {
                $null -ne (Get-Command $_ -ErrorAction SilentlyContinue)
            }
        }
         $webView2 = @(Get-WebView2Installations)
        $report.environment.webView2Versions = @($webView2 | ForEach-Object version)
        if ($webView2.Count -eq 0) {
            throw "Microsoft Edge WebView2 Runtime was not found. This portable spike does not bundle the runtime."
        }
        $report.checks.webView2Runtime = "passed"

        $launchWatch = [Diagnostics.Stopwatch]::StartNew()
        $process = Start-Process -FilePath $executablePath -WorkingDirectory $extractRoot -PassThru
        $deadline = [DateTime]::UtcNow.AddSeconds($WindowTimeoutSeconds)
        $windowHandle = [IntPtr]::Zero
        while ([DateTime]::UtcNow -lt $deadline) {
            $process.Refresh()
            if ($process.HasExited) { throw "The standalone host exited before creating its main window." }
            if ($process.MainWindowHandle -ne [IntPtr]::Zero) {
                $windowHandle = $process.MainWindowHandle
                break
            }
            Start-Sleep -Milliseconds 200
        }
        if ($windowHandle -eq [IntPtr]::Zero) {
            throw "No main window handle appeared within $WindowTimeoutSeconds seconds."
        }
        $launchWatch.Stop()
        $windowTitle = $process.MainWindowTitle
        if ($windowTitle -notmatch "LaunchForge") {
            throw "The process created a window, but its title was unexpected: $windowTitle"
        }
        $report.startupToWindowHandleMs = [Math]::Round($launchWatch.Elapsed.TotalMilliseconds, 2)
        $report.windowTitle = $windowTitle
        $report.checks.applicationWindow = "passed"

        Start-Sleep -Seconds 2
        $snapshot = @(Get-CimInstance -ClassName Win32_Process)
        $treeIds = @(Get-ProcessTreeIds -RootPid $process.Id -Snapshot $snapshot)
        $webViewProcesses = @($snapshot | Where-Object {
            $treeIds -contains [int] $_.ProcessId -and $_.Name -ieq "msedgewebview2.exe"
        })
        $report.observedWebView2ProcessCount = $webViewProcesses.Count

        $smokeDeadline = [DateTime]::UtcNow.AddSeconds($SmokeSeconds)
        while ([DateTime]::UtcNow -lt $smokeDeadline) {
            $process.Refresh()
            if ($process.HasExited) {
                throw "The standalone host exited during the $SmokeSeconds-second smoke window."
            }
            Start-Sleep -Seconds 1
        }
        $report.processId = $process.Id
        $report.checks.processLifetime = "passed"
    }

    $report.status = "passed"
}
catch {
    $report.status = "failed"
    $report.failure = $_.Exception.Message
}
finally {
    if ($null -ne $process) {
        try {
            $snapshot = @(Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue)
            $treeIds = @(Get-ProcessTreeIds -RootPid $process.Id -Snapshot $snapshot)
            foreach ($id in $treeIds) {
                if ($id -ne $process.Id) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
            }
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        catch {
            # Cleanup must not hide the original validation result.
        }
    }
    if ($null -ne $archive) { $archive.Dispose() }
    if ($extractRoot -and (Test-Path -LiteralPath $extractRoot)) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    }

    $report.completedAtUtc = [DateTime]::UtcNow.ToString("o")
    $reportPath = [IO.Path]::GetFullPath($OutputPath)
    $reportDirectory = [IO.Path]::GetDirectoryName($reportPath)
    if ($reportDirectory) { [void] [IO.Directory]::CreateDirectory($reportDirectory) }
    $json = ConvertTo-Json -InputObject $report -Depth 10
    [IO.File]::WriteAllText($reportPath, $json, (New-Object System.Text.UTF8Encoding($false)))
}

if ($report.status -ne "passed") {
    Write-Host "Phase 0 package verification FAILED: $($report.failure)" -ForegroundColor Red
    Write-Host "Report: $([IO.Path]::GetFullPath($OutputPath))"
    exit 1
}

Write-Host "Phase 0 package verification PASSED."
Write-Host "Report: $([IO.Path]::GetFullPath($OutputPath))"
if (-not $ValidateOnly) {
    Write-Host "Startup to main-window handle: $($report.startupToWindowHandleMs) ms (not first-frame latency)."
}
