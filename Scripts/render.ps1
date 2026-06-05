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
  pwsh Scripts/render.ps1 -DataFile Cards.en-US.xlsx -OutputFile Chromatyx-en-US.pdf
#>
param(
  [string]$ScriptFile = (Join-Path $PSScriptRoot '..\Game.nde'),
  [string]$OutputFile = (Join-Path $PSScriptRoot '..\Chromatyx.pdf'),
  [string]$DataFile = '',                         # overrides the script's LINK data file (localized deck data)
  [string]$ToolDir = (Join-Path ([IO.Path]::GetTempPath()) 'nandeck'),
  [string[]]$DownloadUrls = @(
    'https://nandeck.com/download/471/',          # portable zip, v1.29
    'http://www.nand.it/nandeck/nandeck.zip'      # author's legacy mirror
  ),
  # Pin of the v1.29 zip (identical on both mirrors); bump together with the URLs.
  [string]$Sha256 = '1f1b10dec0f642ce42c12e14f194c9d00199f2cff89b250c03a132b93988df09',
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
      $hash = (Get-FileHash -Path $zip -Algorithm SHA256).Hash
      if ($hash -ne $Sha256) {
        Write-Warning "Checksum mismatch from $url (got $hash, expected $Sha256) - a new nanDECK version was probably published; verify it and update the pin."
        continue
      }
      $downloaded = $true
      break
    } catch {
      Write-Warning "Download from $url failed: $($_.Exception.Message)"
    }
  }
  if (-not $downloaded) { throw "nanDECK could not be downloaded (or verified against the pinned SHA-256) from any mirror: $($DownloadUrls -join ', ')" }
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

# nanDECK has no CLI override for the LINK data file (script labels cannot be
# defaulted conditionally: "Label definition not supported between IF/ENDIF"),
# so a localized render patches the LINK line into a temporary sibling script.
# The copy must live next to the original so relative asset paths resolve; the
# encoding is cp1252 (the format's native one) and must round-trip unchanged.
$temporaryScript = $null
if ($DataFile) {
  $cp1252 = [Text.Encoding]::GetEncoding(1252)
  $patched = [IO.File]::ReadAllText($scriptPath, $cp1252) -replace '(?m)^LINK=.*$', "LINK=$DataFile"
  $temporaryScript = Join-Path (Split-Path $scriptPath) ("~render_" + [IO.Path]::GetFileName($scriptPath))
  [IO.File]::WriteAllText($temporaryScript, $patched, $cp1252)
  $scriptPath = $temporaryScript
}

$renderedPdf = [IO.Path]::ChangeExtension($scriptPath, '.pdf')
Remove-Item $renderedPdf, $log -ErrorAction SilentlyContinue

try {
  Write-Host "Rendering $scriptPath $(if ($DataFile) { "with data file $DataFile " })..."
  $process = Start-Process -FilePath $exe -ArgumentList "`"$scriptPath`"", '/createpdf' -PassThru
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $process.Kill()
    if (Test-Path $log) { Get-Content $log | Write-Host }
    throw "nanDECK did not finish within $TimeoutSeconds seconds"
  }
} finally {
  if ($temporaryScript) { Remove-Item $temporaryScript -ErrorAction SilentlyContinue }
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
