param([int]$Port = 8504)

$pythonCandidates = @(
    "$env:LocalAppData\Programs\Python\Python313\python.exe",
    "python"
)
$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python") {
        try { $null = & $candidate --version 2>$null; $pythonExe = $candidate; break } catch {}
    } elseif (Test-Path $candidate) { $pythonExe = $candidate; break }
}
if (-not $pythonExe) { throw "Python олдсонгүй." }

Write-Host "App эхэлж байна: http://localhost:$Port" -ForegroundColor Cyan
& $pythonExe -m streamlit run (Join-Path $PSScriptRoot "app.py") --server.headless true --server.port $Port
