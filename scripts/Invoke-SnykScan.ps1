#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Runs the same Snyk scans locally that CI runs in .github/workflows/snyk.yml.

.DESCRIPTION
    Keeps local and CI results comparable, so a finding can be reproduced and
    fixed before pushing rather than after a red build.

    Prerequisites:
      winget install Snyk.Snyk   # or: npm install -g snyk
      snyk auth                  # one-time browser login

.PARAMETER SeverityThreshold
    Lowest severity to report. CI uses 'high'; drop to 'medium' or 'low' to see
    the full picture locally.

.PARAMETER Sarif
    Also write snyk-sca.sarif / snyk-code.sarif, as CI does before uploading them
    to GitHub code scanning.

.PARAMETER Monitor
    Snapshot the project to snyk.io. CI does this only on pushes to the default
    branch; running it from a feature branch overwrites that snapshot.

.EXAMPLE
    ./scripts/Invoke-SnykScan.ps1

.EXAMPLE
    ./scripts/Invoke-SnykScan.ps1 -SeverityThreshold medium -Sarif
#>
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '',
    Justification = 'Console-facing script: the colourised status output is the point, and it is never piped into anything.')]
[CmdletBinding()]
param(
    [ValidateSet('low', 'medium', 'high', 'critical')]
    [string] $SeverityThreshold = 'high',

    [switch] $Sarif,

    [switch] $Monitor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$cli = Get-Command 'snyk' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $cli) {
    $cli = Get-Command 'snyk-win' -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if (-not $cli) {
    throw "Snyk CLI not found on PATH. Install it with: winget install Snyk.Snyk"
}

$script:Failed = [System.Collections.Generic.List[string]]::new()

function Invoke-SnykStep {
    param(
        [Parameter(Mandatory)] [string]   $Label,
        [Parameter(Mandatory)] [string[]] $Arguments
    )

    Write-Host ''
    Write-Host "=== $Label ===" -ForegroundColor Cyan

    & $cli.Source @Arguments
    $code = $LASTEXITCODE

    # Snyk exit codes: 0 clean, 1 issues found, 2 CLI error, 3 nothing to scan.
    switch ($code) {
        0 { Write-Host "${Label}: clean" -ForegroundColor Green }
        1 {
            Write-Host "${Label}: issues at or above '$SeverityThreshold'" -ForegroundColor Red
            $script:Failed.Add($Label)
        }
        3 { Write-Host "${Label}: nothing supported to scan (CI ignores this too)" -ForegroundColor Yellow }
        default {
            Write-Host "${Label}: CLI error (exit $code)" -ForegroundColor Red
            $script:Failed.Add($Label)
        }
    }
}

Push-Location (Join-Path $PSScriptRoot '..')
try {
    $scaArgs = @('test', '--all-projects', "--severity-threshold=$SeverityThreshold")
    if ($Sarif) { $scaArgs += '--sarif-file-output=snyk-sca.sarif' }
    Invoke-SnykStep -Label 'Snyk Open Source' -Arguments $scaArgs

    $codeArgs = @('code', 'test', "--severity-threshold=$SeverityThreshold")
    if ($Sarif) { $codeArgs += '--sarif-file-output=snyk-code.sarif' }
    Invoke-SnykStep -Label 'Snyk Code' -Arguments $codeArgs

    if ($Monitor) {
        Invoke-SnykStep -Label 'Snyk Monitor' -Arguments @('monitor', '--all-projects')
    }

    Write-Host ''
    if ($script:Failed.Count -gt 0) {
        Write-Host "FAILED: $($script:Failed -join ', ')" -ForegroundColor Red
        exit 1
    }

    Write-Host 'All Snyk scans passed.' -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
