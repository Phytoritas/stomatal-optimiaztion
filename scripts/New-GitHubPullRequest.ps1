param(
    [Nullable[int]]$IssueNumber,
    [string]$Title,
    [string]$BodyFile,
    [string]$Repo,
    [string]$Project = "Phytoritas's Portfolio",
    [string]$Owner = "@me",
    [switch]$Draft,
    [switch]$MarkValidating = $true,
    [switch]$RefreshProjectScope
)

. "$PSScriptRoot/GitHubProject.Common.ps1"

Assert-Command gh
Assert-GhAuth

if ($RefreshProjectScope) {
    & gh auth refresh -s project | Out-Host
}
if (-not $Repo) {
    $Repo = Get-CurrentRepo
}

$projectInfo = Get-ProjectInfo -Owner $Owner -Project $Project
$projectTitle = $projectInfo.Title

if (-not $BodyFile) {
    $template = Get-LocalProjectTemplatePath -RelativePath ".github\pull_request_template.md"
    $tempPath = Join-Path $env:TEMP ("pr-body-" + [guid]::NewGuid().ToString() + ".md")
    $body = Get-Content $template -Raw
    if ($IssueNumber) {
        $body = [regex]::Replace($body, 'Closes\s+#\s*$', "Closes #$IssueNumber")
        if ($body -notmatch "Closes\s+#$IssueNumber") {
            $body = $body.TrimEnd() + "`r`n`r`nCloses #$IssueNumber`r`n"
        }
    }
    Set-Content -Path $tempPath -Value $body -NoNewline
    $BodyFile = $tempPath
}

$prArgs = @(
    "pr", "create",
    "--repo", $Repo,
    "--project", $projectTitle,
    "--body-file", $BodyFile
)
if ($Title) { $prArgs += @("--title", $Title) } else { $prArgs += "--fill" }
if ($Draft) { $prArgs += "--draft" }

$prUrl = ConvertTo-TrimmedString -Value (& gh @prArgs)
if (-not $prUrl) { throw "Failed to create PR." }

if ($IssueNumber -and $MarkValidating) {
    $refreshArgs = @()
    if ($RefreshProjectScope) { $refreshArgs += "-RefreshProjectScope" }

    try {
        & (Join-Path $PSScriptRoot "Set-GitHubProjectStatus.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $IssueNumber -Status Validating -AddIfMissing @refreshArgs
        & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $IssueNumber -FieldName "Stage" -Value "Validating" -Kind "single-select" -AddIfMissing @refreshArgs
    }
    catch {
        Write-Warning "PR created, but project status sync failed: $($_.Exception.Message)"
    }
}

Write-Host "PR URL: $prUrl"