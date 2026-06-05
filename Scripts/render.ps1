<#
.SYNOPSIS
  Renders the Chromatyx print-and-play PDF from the nanDECK script.

.DESCRIPTION
  Downloads the portable nanDECK build (cached between runs via -ToolDir),
  enables its batch mode, renders the deck headless and verifies the result.
  nanDECK does not report script errors through its exit code, so success is
  gated on the output PDF existing and having a plausible size; the nanDECK
  log is printed on failure.

.EXAMPLE
  pwsh Scripts/render.ps1
  pwsh Scripts/render.ps1 -OutputFile out/Chromatyx.pdf -TimeoutSeconds 300
#>
param(
  [string]$ScriptFile = (Join-Path $PSScriptRoot '..\Game.nde'),
  [string]$OutputFile = (Join-Path $PSScriptRoot '..\Chromatyx.pdf'),
  [string]$ToolDir = (Join-Path ([IO.Path]::GetTempPath()) 'nandeck'),
  [string[]]$DownloadUrls = @(
    'https://nandeck.com/download/471/',          # portable zip, v1.29
    'http://www.nand.it/nandeck/nandeck.zip'      # author's legacy mirror
  ),
  [int]$TimeoutSeconds = 600,
  [long]$MinimumBytes = 1MB
)

$ErrorActionPreference = 'Stop'
$exe = Join-Path $ToolDir 'nanDECK.exe'
$log = Join-Path $ToolDir 'nanDECK.log'

# --- provision nanDECK (idempotent, cache-friendly) --------------------------
if (-not (Test-Path $exe)) {
  New-Item -ItemType Directory -Force -Path $ToolDir | Out-Null
  $zip = Join-Path $ToolDir 'nandeck.zip'
  $downloaded = $false
  foreach ($url in $DownloadUrls) {
    try {
      Write-Host "Downloading nanDECK from $url ..."
      Invoke-WebRequest -Uri $url -OutFile $zip -ConnectionTimeoutSeconds 30 -MaximumRetryCount 3 -RetryIntervalSec 10
      $downloaded = $true
      break
    } catch {
      Write-Warning "Download from $url failed: $($_.Exception.Message)"
    }
  }
  if (-not $downloaded) { throw "nanDECK could not be downloaded from any mirror: $($DownloadUrls -join ', ')" }
  Expand-Archive -Path $zip -DestinationPath $ToolDir -Force
  if (-not (Test-Path $exe)) { throw "Downloaded archive did not contain nanDECK.exe" }
}

# Batch actions are ignored unless enabled in the configuration; also keep the
# run quiet: no PDF viewer afterwards, no update check, log to file instead.
@(
  '[main]'
  'enable_batch=1'
  'pdf_open=0'
  'checkver=0'
  'writelog=1'
) | Set-Content -Path (Join-Path $ToolDir 'nanDECK.ini') -Encoding ascii

# --- render -------------------------------------------------------------------
$scriptPath = (Resolve-Path $ScriptFile).Path
$renderedPdf = [IO.Path]::ChangeExtension($scriptPath, '.pdf')
Remove-Item $renderedPdf, $log -ErrorAction SilentlyContinue

Write-Host "Rendering $scriptPath ..."
$process = Start-Process -FilePath $exe -ArgumentList "`"$scriptPath`"", '/createpdf' -PassThru
if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
  $process.Kill()
  if (Test-Path $log) { Get-Content $log | Write-Host }
  throw "nanDECK did not finish within $TimeoutSeconds seconds"
}

# --- verify -------------------------------------------------------------------
if (-not (Test-Path $renderedPdf)) {
  if (Test-Path $log) { Get-Content $log | Write-Host }
  throw "nanDECK exited without producing $renderedPdf - see log above"
}
$pdf = Get-Item $renderedPdf
if ($pdf.Length -lt $MinimumBytes) {
  if (Test-Path $log) { Get-Content $log | Write-Host }
  throw "Rendered PDF is implausibly small ($($pdf.Length) bytes < $MinimumBytes) - the deck is probably incomplete"
}

$outputDir = Split-Path -Parent ([IO.Path]::GetFullPath($OutputFile))
if ($outputDir) { New-Item -ItemType Directory -Force -Path $outputDir | Out-Null }
Move-Item -Path $renderedPdf -Destination $OutputFile -Force
Write-Host "OK: $((Get-Item $OutputFile).FullName) ($([math]::Round($pdf.Length / 1MB, 1)) MB)"
