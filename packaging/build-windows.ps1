param(
    [string]$Version = "0.0.0-dev",
    [switch]$SkipInstaller,
    [string]$WinSWBinary = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Find-InnoCompiler {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    return $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

function Get-WinSWBinary {
    param(
        [Parameter(Mandatory = $true)][string]$Destination,
        [string]$LocalBinary = ""
    )

    $ExpectedHash = "05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da"
    $BundledCandidate = Join-Path $RepoRoot "packaging\windows\vendor\WinSW-x64.exe"
    $SourceBinary = if ($LocalBinary) { $LocalBinary } elseif (Test-Path $BundledCandidate) { $BundledCandidate } else { "" }

    if ($SourceBinary) {
        $ResolvedSource = (Resolve-Path $SourceBinary -ErrorAction Stop).Path
        Copy-Item $ResolvedSource $Destination -Force
    } else {
        $DownloadUrl = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
        $TemporaryDownload = "$Destination.download"
        Remove-Item $TemporaryDownload -Force -ErrorAction SilentlyContinue
        $Downloaded = $false

        $Curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($Curl) {
            Write-Host "Downloading the pinned WinSW service wrapper with curl..."
            & $Curl.Source `
                --fail `
                --location `
                --retry 3 `
                --retry-delay 2 `
                --connect-timeout 30 `
                --output $TemporaryDownload `
                $DownloadUrl
            $Downloaded = ($LASTEXITCODE -eq 0) -and (Test-Path $TemporaryDownload)
        }

        if (-not $Downloaded) {
            Write-Host "curl could not download WinSW; trying Invoke-WebRequest..."
            try {
                Invoke-WebRequest -Uri $DownloadUrl -OutFile $TemporaryDownload -TimeoutSec 120
                $Downloaded = Test-Path $TemporaryDownload
            } catch {
                $Downloaded = $false
            }
        }

        if (-not $Downloaded) {
            Remove-Item $TemporaryDownload -Force -ErrorAction SilentlyContinue
            throw "WinSW could not be downloaded. Download WinSW-x64.exe v2.12.0 manually and rerun with -WinSWBinary <path>, or use -SkipInstaller for the portable ZIP."
        }
        Move-Item $TemporaryDownload $Destination -Force
    }

    $ActualHash = (Get-FileHash $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualHash -ne $ExpectedHash) {
        Remove-Item $Destination -Force -ErrorAction SilentlyContinue
        throw "WinSW checksum mismatch. Expected $ExpectedHash, got $ActualHash."
    }
}

python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean packaging\FlowWorklist.spec

$DistDir = Join-Path $RepoRoot "dist\FlowWorklist"
& "$DistDir\FlowWorklist.exe" --role diagnostics
if ($LASTEXITCODE -ne 0) { throw "Packaged runtime diagnostics failed (exit code $LASTEXITCODE)." }
New-Item "$DistDir\portable.mode" -ItemType File -Force | Out-Null
Compress-Archive -Path "$DistDir\*" -DestinationPath "dist\FlowWorklist-Portable-$Version-Windows-x64.zip" -Force

if (-not $SkipInstaller) {
    Copy-Item "packaging\windows\FlowWorklistService.xml" "$DistDir\FlowWorklistService.xml" -Force
    Get-WinSWBinary -Destination (Join-Path $DistDir "FlowWorklistService.exe") -LocalBinary $WinSWBinary

    $CompilerPath = Find-InnoCompiler
    if (-not $CompilerPath) {
        $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $Winget) {
            throw "Inno Setup was not found and winget is unavailable. Install JRSoftware.InnoSetup or use -SkipInstaller."
        }

        Write-Host "Inno Setup was not found. Installing it for the current user with winget..."
        & $Winget.Source install `
            --id JRSoftware.InnoSetup `
            --exact `
            --scope user `
            --silent `
            --accept-package-agreements `
            --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "winget could not install Inno Setup (exit code $LASTEXITCODE)."
        }
        $CompilerPath = Find-InnoCompiler
    }

    if (-not $CompilerPath) {
        throw "Inno Setup was installed but ISCC.exe could not be located. Open a new terminal and run the build again."
    }
    & $CompilerPath "/DMyAppVersion=$Version" "packaging\windows\FlowWorklist.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed (exit code $LASTEXITCODE)." }
}
