$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$Root\Scripts\Activate.ps1") { & "$Root\Scripts\Activate.ps1" }
python "$Root\flow.py" $args
