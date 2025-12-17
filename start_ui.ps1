# MWLSCP Service Manager - App (Web UI) Launcher
# Launch the App without a visible terminal window

$WorkDir = "C:\Users\benjamin.vieira\Documents\FlowWorklist"
$PythonExe = "$WorkDir\Scripts\python.exe"
$AppPath = "$WorkDir\webui\app.py"

Set-Location $WorkDir

# Activate venv
& "$WorkDir\Scripts\Activate.ps1"

# Start App in background with no visible window
$ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$ProcessInfo.FileName = $PythonExe
$ProcessInfo.Arguments = "\"$WorkDir\webui\app.py\""
$ProcessInfo.WorkingDirectory = $WorkDir
$ProcessInfo.UseShellExecute = $false
$ProcessInfo.CreateNoWindow = $true
$ProcessInfo.RedirectStandardOutput = $true
$ProcessInfo.RedirectStandardError = $true

$Process = [System.Diagnostics.Process]::Start($ProcessInfo)
Write-Host "App started with PID: $($Process.Id)"

# Wait for App to be ready
Start-Sleep -Seconds 3

# Open browser
Start-Process "http://127.0.0.1:5000"

Write-Host "App is running in background: http://127.0.0.1:5000"
Write-Host "Use 'flow stopapp' to stop safely"

# Keep script running
while ($Process.HasExited -eq $false) {
    Start-Sleep -Seconds 1
}
