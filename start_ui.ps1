# MWLSCP Service Manager - Flask Web UI Launcher
# Executa Flask sem janela de terminal visível

$WorkDir = "C:\Users\benjamin.vieira\Documents\FlowWorklist"
$PythonExe = "$WorkDir\Scripts\python.exe"
$AppPath = "$WorkDir\webui\app.py"

Set-Location $WorkDir

# Ativar venv
& "$WorkDir\Scripts\Activate.ps1"

# Iniciar Flask em background sem janela visível
$ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$ProcessInfo.FileName = $PythonExe
$ProcessInfo.Arguments = "-m flask run --host=127.0.0.1 --port=5000"
$ProcessInfo.WorkingDirectory = $WorkDir
$ProcessInfo.UseShellExecute = $false
$ProcessInfo.CreateNoWindow = $true
$ProcessInfo.RedirectStandardOutput = $true
$ProcessInfo.RedirectStandardError = $true

$Process = [System.Diagnostics.Process]::Start($ProcessInfo)
Write-Host "Flask iniciado com PID: $($Process.Id)"

# Aguardar Flask ficar pronto
Start-Sleep -Seconds 3

# Abrir navegador
Start-Process "http://127.0.0.1:5000"

Write-Host "Flask está rodando em background: http://127.0.0.1:5000"
Write-Host "Pressione CTRL+C para parar"

# Manter script rodando
while ($Process.HasExited -eq $false) {
    Start-Sleep -Seconds 1
}
