param(
    [string]$Project = "Phytoritas's Portfolio",
    [string]$Owner = "@me",
    [ValidateSet("Inbox","Ready","Running","Blocked","Validating","Done")]
    [Parameter(Mandatory = $true)][string]$Status,
    [string]$Repo,
    [Nullable[int]]$IssueNumber,
    [Nullable[int]]$PullRequestNumber,
    [string]$ItemUrl,
    [switch]$AddIfMissing = $true,
    [switch]$RefreshProjectScope
)

$script = Join-Path $PSScriptRoot "Set-GitHubProjectField.ps1"
$params = @{
    Project = $Project
    Owner = $Owner
    FieldName = "Status"
    Value = $Status
    Kind = "single-select"
    AddIfMissing = [bool]$AddIfMissing
}

if ($Repo) { $params.Repo = $Repo }
if ($IssueNumber) { $params.IssueNumber = $IssueNumber }
if ($PullRequestNumber) { $params.PullRequestNumber = $PullRequestNumber }
if ($ItemUrl) { $params.ItemUrl = $ItemUrl }
if ($RefreshProjectScope) { $params.RefreshProjectScope = $true }

& $script @params