function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Assert-GhAuth {
    try {
        $null = & gh auth status 2>$null
    } catch {
        throw "GitHub CLI is not authenticated. Run 'gh auth login' first."
    }
}

function ConvertTo-TrimmedString {
    param([AllowNull()]$Value)
    if ($null -eq $Value) {
        return ""
    }
    return ([string]$Value).Trim()
}

function Get-GitRootSafe {
    try {
        $root = ConvertTo-TrimmedString -Value (& git rev-parse --show-toplevel 2>$null)
        if ($root) { return $root }
        return $null
    } catch {
        return $null
    }
}

function Get-CurrentRepo {
    $repo = ConvertTo-TrimmedString -Value (& gh repo view --json nameWithOwner -q .nameWithOwner 2>$null)
    if (-not $repo) {
        throw "Could not resolve current GitHub repository. Run this inside a repository connected to GitHub or pass -Repo."
    }
    return $repo
}

function Resolve-ProjectOwner {
    param([string]$Owner = "@me")
    if ($Owner -and $Owner -ne "@me") {
        return $Owner
    }
    $login = ConvertTo-TrimmedString -Value (& gh api user --jq .login)
    if (-not $login) {
        throw "Could not resolve authenticated GitHub user."
    }
    return $login
}

function New-Slug {
    param([Parameter(Mandatory = $true)][string]$Text)
    $slug = $Text.ToLowerInvariant() -replace '[^a-z0-9]+','-' -replace '(^-+|-+$)',''
    if (-not $slug) { $slug = "work-item" }
    return $slug
}

function Get-DefaultBranchPrefix {
    param([Parameter(Mandatory = $true)][string]$Type)
    switch ($Type) {
        "Hypothesis"     { return "hyp" }
        "Experiment Run" { return "exp" }
        "Model Change"   { return "feat" }
        "Data Prep"      { return "data" }
        "Bug"            { return "fix" }
        "Doc"            { return "docs" }
        default           { return "task" }
    }
}

function Get-DefaultTypeOption {
    param([Parameter(Mandatory = $true)][string]$Type)
    return $Type
}

function Resolve-ItemUrl {
    param(
        [string]$Repo,
        [string]$ItemUrl,
        [Nullable[int]]$IssueNumber,
        [Nullable[int]]$PullRequestNumber
    )

    if ($ItemUrl) { return $ItemUrl }
    if (-not $Repo) { $Repo = Get-CurrentRepo }

    if ($IssueNumber) {
        return "https://github.com/$Repo/issues/$IssueNumber"
    }
    if ($PullRequestNumber) {
        return "https://github.com/$Repo/pull/$PullRequestNumber"
    }
    throw "Provide -ItemUrl, -IssueNumber, or -PullRequestNumber."
}

function Get-TemplateRepoRoot {
    param([string]$ScriptRoot = $PSScriptRoot)

    $scriptHome = Split-Path -Parent $ScriptRoot
    $workspaceCandidate = Join-Path $scriptHome "templates\repo"
    if (Test-Path (Join-Path $workspaceCandidate "AGENTS.md")) {
        return (Resolve-Path $workspaceCandidate).Path
    }

    $repoCandidate = $scriptHome
    if ((Test-Path (Join-Path $repoCandidate "AGENTS.md")) -and (Test-Path (Join-Path $repoCandidate ".github"))) {
        return (Resolve-Path $repoCandidate).Path
    }

    $gitRoot = Get-GitRootSafe
    if ($gitRoot -and (Test-Path (Join-Path $gitRoot ".github"))) {
        return $gitRoot
    }

    throw "Could not resolve template/repo root from script context."
}

function Get-WorkspaceRootFromScript {
    param([string]$ScriptRoot = $PSScriptRoot)
    return (Resolve-Path (Join-Path $ScriptRoot "..")).Path
}

function Get-LocalProjectTemplatePath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $templateRoot = Get-TemplateRepoRoot
    $candidate = Join-Path $templateRoot $RelativePath
    if (-not (Test-Path $candidate)) {
        throw "Template path not found: $candidate"
    }
    return $candidate
}

function Get-ProjectInfo {
    param(
        [string]$Owner = "@me",
        [Parameter(Mandatory = $true)][string]$Project
    )

    $ownerLogin = Resolve-ProjectOwner -Owner $Owner
    $json = & gh project list --owner $ownerLogin --format json
    if (-not $json) { throw "Could not list GitHub Projects for owner '$ownerLogin'." }
    $projects = $json | ConvertFrom-Json
    $normalizedProject = $Project.TrimStart('@')
    $match = $projects.projects |
        Where-Object { $_.title -eq $Project -or $_.title.TrimStart('@') -eq $normalizedProject } |
        Select-Object -First 1
    if (-not $match) {
        throw "Project '$Project' not found for owner '$ownerLogin'."
    }
    [PSCustomObject]@{
        Owner  = $ownerLogin
        Title  = $match.title
        Number = $match.number
        Id     = $match.id
    }
}

function Get-ProjectFieldInfo {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$FieldName
    )

    $query = (
        'query($project:ID!) {' ,
        '  node(id:$project) {' ,
        '    ... on ProjectV2 {' ,
        '      fields(first:100) {' ,
        '        nodes {' ,
        '          __typename' ,
        '          ... on ProjectV2FieldCommon { id name }' ,
        '          ... on ProjectV2SingleSelectField {' ,
        '            id' ,
        '            name' ,
        '            options { id name }' ,
        '          }' ,
        '        }' ,
        '      }' ,
        '    }' ,
        '  }' ,
        '}'
    ) -join "`n"

    $raw = & gh api graphql -f query=$query -F project=$ProjectId
    if (-not $raw) { throw "Could not query project fields." }
    $data = $raw | ConvertFrom-Json
    $field = $data.data.node.fields.nodes | Where-Object { $_.name -eq $FieldName } | Select-Object -First 1
    if (-not $field) {
        throw "Field '$FieldName' not found in the project."
    }
    return $field
}

function Get-ProjectItemsConnection {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [string]$After
    )

    $query = (
        'query($project:ID!, $after:String) {' ,
        '  node(id:$project) {' ,
        '    ... on ProjectV2 {' ,
        '      items(first:100, after:$after) {' ,
        '        nodes {' ,
        '          id' ,
        '          content {' ,
        '            __typename' ,
        '            ... on Issue { url }' ,
        '            ... on PullRequest { url }' ,
        '            ... on DraftIssue { id }' ,
        '          }' ,
        '        }' ,
        '        pageInfo {' ,
        '          hasNextPage' ,
        '          endCursor' ,
        '        }' ,
        '      }' ,
        '    }' ,
        '  }' ,
        '}'
    ) -join "`n"

    $args = @("api", "graphql", "-f", "query=$query", "-F", "project=$ProjectId")
    if ($After) {
        $args += @("-f", "after=$After")
    }

    $raw = & gh @args
    if (-not $raw) { throw "Could not query project items." }
    $data = $raw | ConvertFrom-Json
    $items = $data.data.node.items
    if (-not $items) { throw "Could not query project items." }
    return $items
}

function Find-ProjectItemId {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$ItemUrl
    )

    $after = $null
    while ($true) {
        $items = Get-ProjectItemsConnection -ProjectId $ProjectId -After $after
        $match = $items.nodes | Where-Object { $_.content.url -eq $ItemUrl } | Select-Object -First 1
        if ($match) {
            return $match.id
        }

        $pageInfo = $items.pageInfo
        $hasNextPage = $false
        if ($pageInfo) {
            $hasNextPage = [bool]$pageInfo.hasNextPage
        }
        $after = ConvertTo-TrimmedString -Value $pageInfo.endCursor
        if (-not $hasNextPage -or -not $after) {
            break
        }
    }

    return $null
}

function Wait-ProjectItemId {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$ItemUrl,
        [int]$Attempts = 5,
        [int]$DelaySeconds = 1
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $itemId = Find-ProjectItemId -ProjectId $ProjectId -ItemUrl $ItemUrl
        if ($itemId) {
            return $itemId
        }
        if ($attempt -lt $Attempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $null
}

function Ensure-ProjectItem {
    param(
        [Parameter(Mandatory = $true)][string]$Owner,
        [Parameter(Mandatory = $true)][int]$ProjectNumber,
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$ItemUrl,
        [switch]$AddIfMissing = $true
    )

    $existingId = Find-ProjectItemId -ProjectId $ProjectId -ItemUrl $ItemUrl
    if ($existingId) { return $existingId }

    if (-not $AddIfMissing) {
        throw "Item not found in project and -AddIfMissing was not specified: $ItemUrl"
    }

    & gh project item-add $ProjectNumber --owner $Owner --url $ItemUrl | Out-Null

    $addedId = Wait-ProjectItemId -ProjectId $ProjectId -ItemUrl $ItemUrl
    if (-not $addedId) {
        throw "Failed to add project item: $ItemUrl"
    }
    return $addedId
}

function Set-ProjectFieldValue {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$ItemId,
        [Parameter(Mandatory = $true)][string]$FieldId,
        [Parameter(Mandatory = $true)][ValidateSet("single-select","text","date","number","clear")] [string]$Kind,
        [string]$OptionId,
        [string]$TextValue,
        [string]$DateValue,
        [double]$NumberValue
    )

    $args = @(
        "project", "item-edit",
        "--id", $ItemId,
        "--project-id", $ProjectId,
        "--field-id", $FieldId
    )

    switch ($Kind) {
        "single-select" { $args += @("--single-select-option-id", $OptionId) }
        "text"          { $args += @("--text", $TextValue) }
        "date"          { $args += @("--date", $DateValue) }
        "number"        { $args += @("--number", "$NumberValue") }
        "clear"         { $args += @("--clear") }
    }

    & gh @args | Out-Null
}
