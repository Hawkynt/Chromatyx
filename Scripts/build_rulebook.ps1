<#
.SYNOPSIS
  Converts a rulebook markdown file into a print-ready A4 PDF via pandoc.

.DESCRIPTION
  Uses pandoc with the typst PDF engine - no TeX installation needed. A
  system-wide pandoc is preferred (GitHub runners ship one); otherwise a
  portable build is downloaded, like typst, pinned by SHA-256 and cached
  between runs via -ToolDir.

.EXAMPLE
  pwsh Scripts/build_rulebook.ps1 -MarkdownFile Rulebook.de-DE.md
  pwsh Scripts/build_rulebook.ps1 -MarkdownFile Rulebook.en-US.md -OutputFile Chromatyx-Rulebook-en-US.pdf
#>
param(
  [Parameter(Mandatory = $true)][string]$MarkdownFile,
  [string]$OutputFile = '',
  [string]$ToolDir = (Join-Path ([IO.Path]::GetTempPath()) 'doctools'),
  [string]$PandocUrl = 'https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-windows-x86_64.zip',
  [string]$PandocSha256 = 'bb808d00fd58762299d64582a9b4c3e4b106cd929e62c5f19bcdcb496f1e54ae',
  [string]$TypstUrl = 'https://github.com/typst/typst/releases/download/v0.14.2/typst-x86_64-pc-windows-msvc.zip',
  [string]$TypstSha256 = '51353994ac83218c3497052e89b2c432c53b9d4439cdc1b361e2ea4798ebfc13',
  [long]$MinimumBytes = 50KB
)

$ErrorActionPreference = 'Stop'

function Get-PinnedTool([string]$Name, [string]$Url, [string]$Sha256, [string]$ExeName) {
  $existing = Get-ChildItem -Path $ToolDir -Recurse -Filter $ExeName -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($existing) { return $existing.FullName }
  Write-Host "Downloading $Name from $Url ..."
  New-Item -ItemType Directory -Force -Path $ToolDir | Out-Null
  $zip = Join-Path $ToolDir "$Name.zip"
  Invoke-WebRequest -Uri $Url -OutFile $zip -ConnectionTimeoutSeconds 30 -MaximumRetryCount 3 -RetryIntervalSec 10
  $hash = (Get-FileHash -Path $zip -Algorithm SHA256).Hash
  if ($hash -ne $Sha256) { throw "$Name checksum mismatch (got $hash, expected $Sha256) - verify the new version and update the pin." }
  Expand-Archive -Path $zip -DestinationPath $ToolDir -Force
  $extracted = Get-ChildItem -Path $ToolDir -Recurse -Filter $ExeName | Select-Object -First 1
  if (-not $extracted) { throw "$Name archive did not contain $ExeName" }
  return $extracted.FullName
}

# --- provision tools ----------------------------------------------------------
$pandoc = (Get-Command pandoc -ErrorAction SilentlyContinue).Source
if (-not $pandoc) { $pandoc = Get-PinnedTool 'pandoc' $PandocUrl $PandocSha256 'pandoc.exe' }
$typst = (Get-Command typst -ErrorAction SilentlyContinue).Source
if (-not $typst) { $typst = Get-PinnedTool 'typst' $TypstUrl $TypstSha256 'typst.exe' }
$env:PATH = (Split-Path $typst) + [IO.Path]::PathSeparator + $env:PATH  # pandoc resolves the engine via PATH

# --- derive defaults from the file name (Rulebook.de-DE.md) -------------------
$parts = [IO.Path]::GetFileName($MarkdownFile).Split('.')
$culture = if ($parts.Length -gt 2) { $parts[1] } else { 'en-US' }
if (-not $OutputFile) { $OutputFile = "Chromatyx-Rulebook-$culture.pdf" }
$language = $culture.Split('-')[0]

# --- convert -------------------------------------------------------------------
Write-Host "Converting $MarkdownFile -> $OutputFile ..."
& $pandoc $MarkdownFile -o $OutputFile --pdf-engine=typst `
  -V mainfont="Segoe UI" -V fontsize=11pt -V lang=$language `
  -V margin-x=16mm -V margin-y=18mm
if ($LASTEXITCODE -ne 0) { throw "pandoc failed with exit code $LASTEXITCODE" }

$pdf = Get-Item $OutputFile
if ($pdf.Length -lt $MinimumBytes) { throw "Rulebook PDF is implausibly small ($($pdf.Length) bytes < $MinimumBytes)" }
Write-Host "OK: $($pdf.FullName) ($([math]::Round($pdf.Length / 1KB)) KiB)"
