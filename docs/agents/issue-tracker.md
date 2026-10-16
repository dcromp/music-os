# Issue tracker: GitHub

Issues and specs for this repo live in [dcromp/music-os](https://github.com/dcromp/music-os/issues).
Use the `gh` CLI with `--repo dcromp/music-os` (or `-R dcromp/music-os`) for
repository operations. This chat can start in another checkout; always verify
the repository rather than relying on the shell's current folder.

## Conventions

- **Create an issue**: `gh issue create --repo dcromp/music-os --title "..." --body-file <file>`. Write the exact Markdown body to a file first.
- **Read an issue**: `gh issue view <number> --repo dcromp/music-os --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --repo dcromp/music-os --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). Older `gh`: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>` (database id, as in **Blocking** below). Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Comment on an issue**: `gh issue comment <number> --repo dcromp/music-os --body-file <file>`
- **Apply / remove labels**: `gh issue edit <number> --repo dcromp/music-os --add-label "..."` / `gh issue edit <number> --repo dcromp/music-os --remove-label "..."`
- **Close**: `gh issue close <number> --repo dcromp/music-os --reason completed` after posting completion evidence with `--body-file`

Verify `origin` names `dcromp/music-os` before repository work. Keep the `--repo`
argument explicit when using issue commands from another directory.

## Ticket board

[Initial ticket index](tickets.md). Eight approved tickets are published as #2–#9, with six native dependency edges.

GitHub Issues is the task source of truth. `README.md` summarizes current status
and deployment; `plan.md` remains the high-level roadmap.

- **Needs triage:** open issues labelled `needs-triage`.
- **Ready:** `ready-for-agent`, unassigned, with no open native blocker.
- **In progress:** a claimed open ticket assigned to its implementer.
- **Waiting for information:** `needs-info`.
- **Human work:** `ready-for-human`; a required human action must be explicit.
- **Blocked:** an open native dependency; `ready-for-agent` describes a fully
  specified brief, not permission to ignore its blockers.
- **Done:** closed with acceptance evidence and a commit/PR or result link.

Search for an existing ticket before creating one. Record incomplete findings
and the next concrete action when work stops. A diagnostic run completing does
not satisfy an issue that requires verified music or deployment.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (see **Make an issue a sub-issue of a parent**). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
