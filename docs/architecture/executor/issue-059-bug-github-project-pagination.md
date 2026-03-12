## repro
- Run `scripts/New-GitHubIssueBranch.ps1` or `scripts/New-GitHubPullRequest.ps1` after the GitHub Project grows beyond 100 items.
- The GitHub item is added successfully, but the helper prints `Failed to add project item: <url>`.

## expected / actual
- expected: project sync should detect the newly added item and continue to set `Status` / `Stage` fields without warning.
- actual: `Ensure-ProjectItem()` only queries `items(first:100)`, misses items beyond the first page, and raises a false failure.

## scope
- repo-local helper scripts under `scripts/`
- shared workspace helper source at `C:\Users\yhmoo\OneDrive\Phytoritas\scripts\`

## fix idea
- add cursor-based GitHub Project item pagination and retry lookup after `gh project item-add`
- keep the shared workspace script and repo-local copy aligned

## test
- run the updated helper against an existing `stomatal-optimiaztion` issue already on the Project board and confirm field sync works without the false warning
