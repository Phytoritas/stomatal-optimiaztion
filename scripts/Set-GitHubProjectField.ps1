param(
    [string]$Project = "Phytoritas's Portfolio",
    [string]$Owner = "@me",
    [Parameter(Mandatory = $true)][string]$FieldName,
    [string]$Value,
    [ValidateSet("single-select","text","date","number","clear")]
    [string]$Kind = "single-select",
    [string]$Repo,
    [Nullable[int]]$IssueNumber,
    [Nullable[int]]$PullRequestNumber,
    [string]$ItemUrl,
    [switch]$AddIfMissing = $true,
    [switch]$RefreshProjectScope
)

. "$PSScriptRoot/GitHubProject.Common.ps1"

Assert-Command gh
Assert-GhAuth

if ($RefreshProjectScope) {
    & gh auth refresh -s project | Out-Host
}
if (-not $Repo -and -not $ItemUrl) {
    $Repo = Get-CurrentRepo
}

$targetUrl = Resolve-ItemUrl -Repo $Repo -ItemUrl $ItemUrl -IssueNumber $IssueNumber -PullRequestNumber $PullRequestNumber
$projectInfo = Get-ProjectInfo -Owner $Owner -Project $Project
$fieldInfo = Get-ProjectFieldInfo -ProjectId $projectInfo.Id -FieldName $FieldName
$itemId = Ensure-ProjectItem -Owner $projectInfo.Owner -ProjectNumber $projectInfo.Number -ProjectId $projectInfo.Id -ItemUrl $targetUrl -AddIfMissing:$AddIfMissing

switch ($Kind) {
    "single-select" {
        $option = $fieldInfo.options | Where-Object { $_.name -ieq $Value } | Select-Object -First 1
        if (-not $option) {
            $available = ($fieldInfo.options | ForEach-Object { $_.name }) -join ", "
            throw "Single-select option '$Value' not found for field '$FieldName'. Available: $available"
        }
        Set-ProjectFieldValue -ProjectId $projectInfo.Id -ItemId $itemId -FieldId $fieldInfo.id -Kind "single-select" -OptionId $option.id
    }
    "text" {
        Set-ProjectFieldValue -ProjectId $projectInfo.Id -ItemId $itemId -FieldId $fieldInfo.id -Kind "text" -TextValue $Value
    }
    "date" {
        Set-ProjectFieldValue -ProjectId $projectInfo.Id -ItemId $itemId -FieldId $fieldInfo.id -Kind "date" -DateValue $Value
    }
    "number" {
        [double]$n = $Value
        Set-ProjectFieldValue -ProjectId $projectInfo.Id -ItemId $itemId -FieldId $fieldInfo.id -Kind "number" -NumberValue $n
    }
    "clear" {
        Set-ProjectFieldValue -ProjectId $projectInfo.Id -ItemId $itemId -FieldId $fieldInfo.id -Kind "clear"
    }
}

Write-Host "Set field '$FieldName' to '$Value' for $targetUrl"
