param(
    [ValidateSet("Hypothesis","Experiment Run","Model Change","Data Prep","Bug","Doc")]
    [Parameter(Mandatory = $true)][string]$Type,
    [Parameter(Mandatory = $true)][string]$Title,
    [string]$BodyFile,
    [string]$Repo,
    [string]$Project = "Phytoritas's Portfolio",
    [string]$Owner = "@me",
    [string[]]$Labels = @(),
    [string]$Assignee = "@me",
    [switch]$Checkout = $true,
    [switch]$SetRunning = $true,
    [string]$PortfolioStatus = "Active",
    [string]$Crop,
    [string]$Model,
    [string]$NextReviewDate,
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

$templateMap = @{
    "Hypothesis"     = ".github\ISSUE_TEMPLATE\issue-hypothesis.md"
    "Experiment Run" = ".github\ISSUE_TEMPLATE\issue-experiment-run.md"
    "Model Change"   = ".github\ISSUE_TEMPLATE\issue-model-change.md"
    "Data Prep"      = ".github\ISSUE_TEMPLATE\issue-data-prep.md"
    "Bug"            = ".github\ISSUE_TEMPLATE\issue-bug.md"
    "Doc"            = ".github\ISSUE_TEMPLATE\issue-doc.md"
}

if (-not $BodyFile) {
    $BodyFile = Get-LocalProjectTemplatePath -RelativePath $templateMap[$Type]
}

$defaultTypeLabel = switch ($Type) {
    "Hypothesis"     { "type:hypothesis" }
    "Experiment Run" { "type:experiment" }
    "Model Change"   { "type:model-change" }
    "Data Prep"      { "type:data" }
    "Bug"            { "type:bug" }
    "Doc"            { "type:doc" }
}

$allLabels = New-Object System.Collections.Generic.List[string]
if ($defaultTypeLabel) { [void]$allLabels.Add($defaultTypeLabel) }
foreach ($label in $Labels) { if ($label) { [void]$allLabels.Add($label) } }
if ($Model) { [void]$allLabels.Add("model:$Model") }
if ($Crop)  { [void]$allLabels.Add("crop:$Crop") }

$issueArgs = @(
    "issue", "create",
    "--repo", $Repo,
    "--title", "[$Type] $Title",
    "--body-file", $BodyFile,
    "--project", $projectTitle
)

if ($Assignee) { $issueArgs += @("--assignee", $Assignee) }
foreach ($label in $allLabels | Select-Object -Unique) {
    $issueArgs += @("--label", $label)
}

$issueUrl = ConvertTo-TrimmedString -Value (& gh @issueArgs)
if (-not $issueUrl) { throw "Failed to create issue." }
if ($issueUrl -notmatch '/(?<number>\d+)$') {
    throw "Could not parse issue number from URL: $issueUrl"
}
$issueNumber = [int]$Matches.number
$branchPrefix = Get-DefaultBranchPrefix -Type $Type
$branchSlug = New-Slug -Text $Title
$branchName = "$branchPrefix/$issueNumber-$branchSlug"

if ($Checkout) {
    & gh issue develop $issueNumber --repo $Repo --checkout --name $branchName | Out-Null
}

$refreshArgs = @()
if ($RefreshProjectScope) { $refreshArgs += "-RefreshProjectScope" }

try {
    & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -FieldName "Type" -Value (Get-DefaultTypeOption -Type $Type) -Kind "single-select" -AddIfMissing @refreshArgs
    & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -FieldName "Portfolio Status" -Value $PortfolioStatus -Kind "single-select" -AddIfMissing @refreshArgs

    if ($Crop) {
        & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -FieldName "Crop" -Value $Crop -Kind text -AddIfMissing @refreshArgs
    }
    if ($NextReviewDate) {
        & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -FieldName "Next Review Date" -Value $NextReviewDate -Kind date -AddIfMissing @refreshArgs
    }
    if ($SetRunning) {
        & (Join-Path $PSScriptRoot "Set-GitHubProjectStatus.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -Status Running -AddIfMissing @refreshArgs
        & (Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1") -Project $projectTitle -Owner $Owner -Repo $Repo -IssueNumber $issueNumber -FieldName "Stage" -Value "Running" -Kind "single-select" -AddIfMissing @refreshArgs
    }
}
catch {
    Write-Warning "Issue created, but some project fields could not be synced: $($_.Exception.Message)"
}

Write-Host "Issue URL: $issueUrl"
Write-Host "Issue Number: $issueNumber"
Write-Host "Branch Name: $branchName"