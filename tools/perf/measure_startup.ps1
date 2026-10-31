# Start to first screen (SPEC 15), on Joe's Windows machine. A Windows script for the maintainer; the app never runs it.
# It starts the installed Wholecount.exe, waits for its main window, prints the milliseconds, and asks the window to close
# the way a person would (CloseMainWindow), never by stopping the process. Five runs, then the median.
#
#   .\tools\perf\measure_startup.ps1 [-Exe "C:\Program Files\Wholecount\Wholecount.exe"] [-Runs 5]
param(
    [string]$Exe = "C:\Program Files\Wholecount\Wholecount.exe",
    [int]$Runs = 5,
    [int]$TimeoutSeconds = 60
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $Exe)) { throw "Wholecount.exe was not found at the path given." }

$times = @()
for ($i = 1; $i -le $Runs; $i++) {
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $Exe -PassThru
    while ($p.MainWindowHandle -eq 0) {
        if ($clock.Elapsed.TotalSeconds -gt $TimeoutSeconds) { throw "The main window did not appear in time." }
        Start-Sleep -Milliseconds 20
        $p.Refresh()
    }
    $clock.Stop()
    $ms = [int]$clock.Elapsed.TotalMilliseconds
    $times += $ms
    Write-Output "run $i startup_ms $ms"
    [void]$p.CloseMainWindow()
    [void]$p.WaitForExit(30000)
    Start-Sleep -Seconds 2
}
$sorted = $times | Sort-Object
$median = $sorted[[int][math]::Floor($sorted.Count / 2)]
Write-Output "startup_ms $median"
