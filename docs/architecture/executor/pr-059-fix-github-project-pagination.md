## Background
- GitHub Project helper scripts started printing false `Failed to add project item` warnings once the shared Project board grew beyond 100 items.
- The root cause was a first-page-only GraphQL lookup inside `Ensure-ProjectItem()`, so existing or newly added items beyond the first 100 could not be found even when `gh project item-add` succeeded.

## Changes
- add cursor-based Project item pagination helpers in `scripts/GitHubProject.Common.ps1`
- make `Ensure-ProjectItem()` reuse paginated lookup both before and after `gh project item-add`
- add a short retry window after `item-add` so field sync can absorb Project API propagation delay
- mirror the same fix into the shared workspace helper at `C:\Users\yhmoo\OneDrive\Phytoritas\scripts\GitHubProject.Common.ps1`

## Validation
- dot-source repo-local `scripts/GitHubProject.Common.ps1` and resolve the Project item id for `issue #57` with `AddIfMissing:$false`
- dot-source shared `C:\Users\yhmoo\OneDrive\Phytoritas\scripts\GitHubProject.Common.ps1` and resolve the same Project item id
- run repo-local `scripts\Set-GitHubProjectStatus.ps1 -IssueNumber 57 -Status Done`
- run shared `C:\Users\yhmoo\OneDrive\Phytoritas\scripts\Set-GitHubProjectStatus.ps1 -IssueNumber 57 -Status Done`

## Impact
- Project status sync no longer depends on the target item appearing in the first 100 board entries
- repo-local helpers and the shared workspace helper stay aligned for future repos

## Linked issue
Closes #59
