[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $ExecutablePath,
    [Parameter(Mandatory = $true)] [string] $PackagePath,
    [ValidateRange(1, 120)] [int] $WarmupSeconds = 15,
    [ValidateRange(5, 600)] [int] $SampleSeconds = 60,
    [ValidateRange(1, 20)] [int] $Runs = 5,
    [string] $OutputPath = "phase0-measurements.json"
)

$ErrorActionPreference = "Stop"
$exe = (Resolve-Path -LiteralPath $ExecutablePath).Path
$package = (Resolve-Path -LiteralPath $PackagePath).Path
$logicalProcessors = [Environment]::ProcessorCount

function Get-ProcessTreeIds([int] $RootPid) {
    $all = @(Get-CimInstance Win32_Process)
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    [void]$ids.Add($RootPid)
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($item in $all) {
            $pidValue = [int]$item.ProcessId
            if (-not $ids.Contains($pidValue) -and $ids.Contains([int]$item.ParentProcessId)) {
                [void]$ids.Add($pidValue)
                $changed = $true
            }
        }
    }
    return @($ids)
}

function Assert-HostAlive([Diagnostics.Process] $RootProcess, [int] $Run, [string] $Stage) {
    $RootProcess.Refresh()
    if ($RootProcess.HasExited) {
        throw "Application exited during $Stage (run $Run, exit code $($RootProcess.ExitCode))."
    }
    $current = Get-Process -Id $RootProcess.Id -ErrorAction SilentlyContinue
    if ($null -eq $current) {
        throw "Application process disappeared during $Stage (run $Run)."
    }
}

function Get-TreeCounters([int] $RootPid) {
    $rootProcess = Get-Process -Id $RootPid -ErrorAction SilentlyContinue
    if ($null -eq $rootProcess) {
        throw "Application process $RootPid exited while collecting process-tree counters."
    }
    $ids = Get-ProcessTreeIds -RootPid $RootPid
    $items = @(
        foreach ($id in $ids) {
            Get-Process -Id $id -ErrorAction SilentlyContinue
        }
    )
    $items = @($items | Where-Object { $null -ne $_ })
    [double]$cpu = 0
    [long]$workingSet = 0
    foreach ($item in $items) {
        if ($null -ne $item.CPU) { $cpu += [double]$item.CPU }
        $workingSet += [long]$item.WorkingSet64
    }
    if (-not ($items | Where-Object { $_.Id -eq $RootPid })) {
        throw "Application process $RootPid was absent from its process-tree sample."
    }
    return [pscustomobject]@{
        ProcessIds = $ids
        CpuSeconds = $cpu
        WorkingSetBytes = $workingSet
        ProcessCount = $items.Count
    }
}

function Get-Percentile([double[]] $Values, [double] $Percentile) {
    if ($Values.Count -eq 0) { return $null }
    $sorted = @($Values | Sort-Object)
    $index = [Math]::Max(0, [Math]::Ceiling($Percentile * $sorted.Count) - 1)
    return [Math]::Round($sorted[$index], 2)
}

$runResults = [System.Collections.Generic.List[object]]::new()
for ($run = 1; $run -le $Runs; $run++) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $exe -PassThru
    $windowHandleMs = $null
    $observedTreeIds = [System.Collections.Generic.HashSet[int]]::new()
    try {
        $windowDeadline = [DateTime]::UtcNow.AddSeconds(60)
        while ([DateTime]::UtcNow -lt $windowDeadline) {
            $current = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
            if ($null -eq $current) { throw "Application exited before creating a main window (run $run)." }
            if ($current.MainWindowHandle -ne 0) {
                $windowHandleMs = [Math]::Round($watch.Elapsed.TotalMilliseconds, 2)
                break
            }
            Start-Sleep -Milliseconds 100
        }
        if ($null -eq $windowHandleMs) { throw "No main window handle appeared within 60 seconds (run $run)." }
        Start-Sleep -Seconds $WarmupSeconds
        Assert-HostAlive -RootProcess $process -Run $run -Stage "warm-up"

        $first = Get-TreeCounters -RootPid $process.Id
        foreach ($id in $first.ProcessIds) { [void]$observedTreeIds.Add([int]$id) }
        [double]$peakWorkingSet = $first.WorkingSetBytes
        $last = $first
        $sampleWatch = [Diagnostics.Stopwatch]::StartNew()
        while ($sampleWatch.Elapsed.TotalSeconds -lt $SampleSeconds) {
            Start-Sleep -Seconds 1
            Assert-HostAlive -RootProcess $process -Run $run -Stage "sampling"
            $last = Get-TreeCounters -RootPid $process.Id
            foreach ($id in $last.ProcessIds) { [void]$observedTreeIds.Add([int]$id) }
            if ($last.WorkingSetBytes -gt $peakWorkingSet) { $peakWorkingSet = $last.WorkingSetBytes }
        }
        Assert-HostAlive -RootProcess $process -Run $run -Stage "end of sampling"
        $last = Get-TreeCounters -RootPid $process.Id
        foreach ($id in $last.ProcessIds) { [void]$observedTreeIds.Add([int]$id) }
        $sampleWatch.Stop()
        $cpuPercent = (($last.CpuSeconds - $first.CpuSeconds) / [Math]::Max(0.001, $sampleWatch.Elapsed.TotalSeconds) / $logicalProcessors) * 100
        $runResults.Add([pscustomobject]@{
            Run = $run
            StartupToWindowHandleMs = $windowHandleMs
            IdleCpuPercent = [Math]::Round([Math]::Max(0, $cpuPercent), 3)
            SampledPeakProcessTreeWorkingSetMB = [Math]::Round($peakWorkingSet / 1MB, 2)
            SampleSeconds = [Math]::Round($sampleWatch.Elapsed.TotalSeconds, 2)
            ProcessCountAtEnd = $last.ProcessCount
        })
    }
    finally {
        try {
            foreach ($id in (Get-ProcessTreeIds -RootPid $process.Id)) {
                [void]$observedTreeIds.Add([int]$id)
            }
        } catch {
            # The root may already have exited; previously observed descendants are still cleaned up.
        }
        foreach ($id in $observedTreeIds) {
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
        }
    }
}

$files = @(Get-ChildItem -LiteralPath $package -File -Recurse -Force)
[long]$packageBytes = 0
foreach ($file in $files) { $packageBytes += $file.Length }
$os = Get-CimInstance Win32_OperatingSystem
$cpuName = (Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)
$report = [pscustomobject]@{
    RecordedAtUtc = [DateTime]::UtcNow.ToString("o")
    Environment = [pscustomobject]@{
        OS = $os.Caption
        OSVersion = $os.Version
        CPU = $cpuName
        LogicalProcessors = $logicalProcessors
        TotalMemoryMB = [Math]::Round($os.TotalVisibleMemorySize / 1024, 0)
    }
    Configuration = [pscustomobject]@{
        ExecutablePath = $exe
        PackagePath = $package
        WarmupSeconds = $WarmupSeconds
        SampleSeconds = $SampleSeconds
        Runs = $Runs
        PackageFileCount = $files.Count
        ExtractedPackageBytes = $packageBytes
    }
    Summary = [pscustomobject]@{
        StartupToWindowHandleMedianMs = Get-Percentile -Values @($runResults | ForEach-Object StartupToWindowHandleMs) -Percentile 0.50
        StartupToWindowHandleP95Ms = Get-Percentile -Values @($runResults | ForEach-Object StartupToWindowHandleMs) -Percentile 0.95
        IdleCpuMedianPercent = Get-Percentile -Values @($runResults | ForEach-Object IdleCpuPercent) -Percentile 0.50
        SampledPeakWorkingSetP95MB = Get-Percentile -Values @($runResults | ForEach-Object SampledPeakProcessTreeWorkingSetMB) -Percentile 0.95
    }
    Runs = @($runResults)
    Limitations = @(
        "StartupToWindowHandleMs is not first-usable-frame latency.",
        "Idle CPU and sampled peak working set are sampled process-tree estimates; repeat on an otherwise idle machine.",
        "Record compressed installer/archive size separately; ExtractedPackageBytes is the expanded folder size."
    )
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Wrote measurements to $((Resolve-Path -LiteralPath $OutputPath).Path)"
