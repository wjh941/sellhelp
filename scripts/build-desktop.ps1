[CmdletBinding()]
param(
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Invoke-DesktopBuild {
    $repositoryRoot = Split-Path -Parent $PSScriptRoot

    Push-Location $repositoryRoot
    try {
        Invoke-Checked { python -m pip install --no-deps -r backend\requirements-build.txt } 'Installing Python build dependencies'
        Invoke-Checked { npm.cmd --prefix frontend ci } 'Installing frontend dependencies'
        Invoke-Checked { npm.cmd --prefix frontend run build } 'Building frontend assets'

        Push-Location backend
        try {
            Invoke-Checked { python -m PyInstaller --noconfirm --clean SellHelpBackend.spec } 'Building bundled backend'
        }
        finally {
            Pop-Location
        }

        Invoke-Checked { npm.cmd --prefix desktop ci } 'Installing desktop build dependencies'
        Invoke-Checked { npm.cmd --prefix desktop run dist } 'Building Windows installer'
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipBuild) {
    Invoke-DesktopBuild
}
