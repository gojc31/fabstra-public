<#
.SYNOPSIS
  Install or update the user skills and agents shipped in user-skills/ into ~/.claude.

.DESCRIPTION
  Copies user-skills\skills\<name> to <home>\.claude\skills\<name> and
  user-skills\agents\*.md to <home>\.claude\agents\ (their LICENSE goes along as
  user-skills-agents-LICENSE, a non-.md name Claude Code ignores), replacing the
  {{SKILLS_DIR}} placeholder with the real skills folder. A skill folder or
  agent file that already exists and differs is backed up first to
  <home>\.claude\backups\user-skills-<timestamp>\ and then replaced. Skills
  and agents that are not in the repo are never touched.
  Windows PowerShell 5.1 compatible.

.PARAMETER DryRun
  Print what would change; write nothing.

.PARAMETER Home
  Install under this folder instead of your user profile (for testing).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install-user-skills.ps1 -DryRun
#>
param(
    [switch]$DryRun,
    [Alias('Home')][string]$TargetHome
)

$ErrorActionPreference = 'Stop'
$Placeholder = '{{SKILLS_DIR}}'
$CacheDirs = @('__pycache__', '.pytest_cache')

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SrcRoot = Join-Path $RepoRoot 'user-skills'
$SrcSkills = Join-Path $SrcRoot 'skills'
$SrcAgents = Join-Path $SrcRoot 'agents'
if (-not (Test-Path -LiteralPath $SrcSkills -PathType Container)) {
    throw "No user-skills\skills folder at $SrcSkills - run this from a clone of the repo."
}

if ([string]::IsNullOrEmpty($TargetHome)) { $TargetHome = $HOME }
if ([string]::IsNullOrEmpty($TargetHome)) { $TargetHome = [Environment]::GetFolderPath('UserProfile') }
$TargetHome = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($TargetHome)
$TargetHome = [System.IO.Path]::GetFullPath($TargetHome).TrimEnd('\')
$ClaudeDir = Join-Path $TargetHome '.claude'
$DstSkills = Join-Path $ClaudeDir 'skills'
$DstAgents = Join-Path $ClaudeDir 'agents'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $ClaudeDir "backups\user-skills-$Stamp"
$Utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$Sha = [System.Security.Cryptography.SHA256]::Create()
$script:BackedUp = 0

function Get-ExpectedBytes([string]$Path) {
    # File bytes as they should land: the placeholder replaced in UTF-8 text files.
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ([Array]::IndexOf($bytes, [byte]0) -ge 0) { return ,$bytes }
    try { $text = $Utf8Strict.GetString($bytes) } catch { return ,$bytes }
    if ($text.IndexOf($Placeholder) -lt 0) { return ,$bytes }
    return ,$Utf8NoBom.GetBytes($text.Replace($Placeholder, $DstSkills))
}

function Get-Hash([byte[]]$Bytes) {
    return [System.BitConverter]::ToString($Sha.ComputeHash($Bytes))
}

function Get-RelFiles([string]$Root) {
    # Relative paths of every file under $Root, skipping test caches.
    $list = @()
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $list }
    $prefix = $Root.TrimEnd('\').Length + 1
    foreach ($f in Get-ChildItem -LiteralPath $Root -Recurse -File -Force) {
        $rel = $f.FullName.Substring($prefix)
        $parts = $rel.Split('\')
        $skip = $false
        foreach ($p in $parts) { if ($CacheDirs -contains $p) { $skip = $true } }
        if (-not $skip) { $list += $rel }
    }
    return $list
}

function Backup-Item([string]$Path, [string]$Sub) {
    $dest = Join-Path $BackupRoot $Sub
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    Copy-Item -LiteralPath $Path -Destination $dest -Recurse -Force
    $script:BackedUp++
}

function Write-Bytes([string]$Path, [byte[]]$Bytes) {
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    [System.IO.File]::WriteAllBytes($Path, $Bytes)
}

if ($DryRun) { $mode = 'DRY RUN - nothing is written' } else { $mode = 'install' }
Write-Host "user-skills $mode"
Write-Host "  from   $SrcRoot"
Write-Host "  skills $DstSkills"
Write-Host "  agents $DstAgents"

$counts = @{ new = 0; updated = 0; unchanged = 0 }

foreach ($skill in Get-ChildItem -LiteralPath $SrcSkills -Directory | Sort-Object Name) {
    $name = $skill.Name
    $dst = Join-Path $DstSkills $name
    $expected = @{}
    foreach ($rel in Get-RelFiles $skill.FullName) {
        $expected[$rel] = Get-ExpectedBytes (Join-Path $skill.FullName $rel)
    }
    $exists = Test-Path -LiteralPath $dst -PathType Container
    $added = 0; $changed = 0; $removed = 0
    if ($exists) {
        $have = Get-RelFiles $dst
        foreach ($rel in $have) {
            if (-not $expected.ContainsKey($rel)) { $removed++ }
        }
        foreach ($rel in $expected.Keys) {
            $p = Join-Path $dst $rel
            if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { $added++; continue }
            if ((Get-Hash ([System.IO.File]::ReadAllBytes($p))) -ne (Get-Hash $expected[$rel])) { $changed++ }
        }
    }
    if (-not $exists) {
        $status = 'new'
        $detail = "($($expected.Count) files)"
    } elseif (($added + $changed + $removed) -eq 0) {
        $status = 'unchanged'
        $detail = ''
    } else {
        $status = 'updated'
        $detail = "($changed changed, $added added, $removed removed; backup first)"
    }
    $counts[$status]++
    Write-Host ("  skill  {0,-10} {1} {2}" -f $status, $name, $detail)
    if ($DryRun -or $status -eq 'unchanged') { continue }
    if ($exists) {
        Backup-Item $dst ("skills\" + $name)
        Remove-Item -LiteralPath $dst -Recurse -Force
    }
    foreach ($rel in $expected.Keys) { Write-Bytes (Join-Path $dst $rel) $expected[$rel] }
}

if (Test-Path -LiteralPath $SrcAgents -PathType Container) {
    $agentItems = @()
    foreach ($a in Get-ChildItem -LiteralPath $SrcAgents -File -Filter '*.md' | Sort-Object Name) {
        $agentItems += ,@($a.FullName, $a.Name)
    }
    # The agents' licence travels with them under a non-.md name, so Claude Code never loads it as an agent.
    $lic = Join-Path $SrcAgents 'LICENSE'
    if (Test-Path -LiteralPath $lic -PathType Leaf) { $agentItems += ,@($lic, 'user-skills-agents-LICENSE') }
    foreach ($item in $agentItems) {
        $name = $item[1]
        $dst = Join-Path $DstAgents $name
        $bytes = Get-ExpectedBytes $item[0]
        if (-not (Test-Path -LiteralPath $dst -PathType Leaf)) {
            $status = 'new'
        } elseif ((Get-Hash ([System.IO.File]::ReadAllBytes($dst))) -eq (Get-Hash $bytes)) {
            $status = 'unchanged'
        } else {
            $status = 'updated'
        }
        $counts[$status]++
        Write-Host ("  agent  {0,-10} {1}" -f $status, $name)
        if ($DryRun -or $status -eq 'unchanged') { continue }
        if ($status -eq 'updated') { Backup-Item $dst ("agents\" + $name) }
        Write-Bytes $dst $bytes
    }
}

Write-Host ("Summary: {0} new, {1} updated, {2} unchanged." -f $counts['new'], $counts['updated'], $counts['unchanged'])
if ($DryRun) {
    Write-Host 'Dry run: nothing was written.'
} elseif ($script:BackedUp -gt 0) {
    Write-Host "Backup of what was replaced: $BackupRoot"
} else {
    Write-Host 'Nothing existing was replaced, so no backup was needed.'
}
Write-Host 'Skills and agents that are not in the repo were left alone.'
