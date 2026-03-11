param(
    [string]$Repo
)

. "$PSScriptRoot/GitHubProject.Common.ps1"

Assert-Command gh
Assert-GhAuth

if (-not $Repo) {
    $Repo = Get-CurrentRepo
}

$labels = @(
    @{ Name = "type:hypothesis";  Color = "A371F7"; Description = "Hypothesis framing work" },
    @{ Name = "type:experiment";  Color = "1D76DB"; Description = "Experiment run / evaluation" },
    @{ Name = "type:model-change";Color = "5319E7"; Description = "Model or equation change" },
    @{ Name = "type:data";        Color = "0E8A16"; Description = "Data preparation / ingestion" },
    @{ Name = "type:bug";         Color = "D73A4A"; Description = "Bug fix" },
    @{ Name = "type:doc";         Color = "FBCA04"; Description = "Documentation work" },
    @{ Name = "prio:p0";          Color = "B60205"; Description = "Highest priority" },
    @{ Name = "prio:p1";          Color = "D93F0B"; Description = "High priority" },
    @{ Name = "prio:p2";          Color = "FBCA04"; Description = "Normal priority" },
    @{ Name = "model:gosm";       Color = "0052CC"; Description = "Growth-optimizing stomatal model" },
    @{ Name = "model:thorp";      Color = "5319E7"; Description = "Tree hydraulics and optimal resource partitioning" },
    @{ Name = "model:tdgm";       Color = "006B75"; Description = "Turgor-driven growth model" },
    @{ Name = "model:load-cell";  Color = "0E8A16"; Description = "Load-cell data pipeline" },
    @{ Name = "model:general";    Color = "C2E0C6"; Description = "Cross-model or general work" },
    @{ Name = "crop:tomato";      Color = "E11D21"; Description = "Tomato-related work" },
    @{ Name = "crop:cucumber";    Color = "7FDBB6"; Description = "Cucumber-related work" },
    @{ Name = "crop:general";     Color = "CCCCCC"; Description = "Crop-agnostic work" }
)

foreach ($label in $labels) {
    & gh label create $label.Name --repo $Repo --color $label.Color --description $label.Description --force | Out-Null
    Write-Host "Synced label: $($label.Name)"
}

Write-Host "Label sync complete for $Repo"
