# Matt Pocock skills in music-os

The engineering skills are installed for this repository under `.agents/skills/`
from [mattpocock/skills](https://github.com/mattpocock/skills), pinned to commit
`49dd158d1076134a641b33efb035946536778336`. This is a repository-local copy,
not a global plugin installation. It includes all 20 engineering and seven
productivity skills. The upstream MIT licence and a file-hash manifest accompany
the installation.

Repository skill discovery applies to tasks opened in this checkout (or its
subfolders). Use `/Users/davidcrompton/Documents/music-os` as the project folder;
changing a shell command's working directory alone does not change a chat's
startup context. The skills are available on the next turn in that repository
context; if a selector remains stale, restart Codex. An existing chat can read
the corresponding `SKILL.md` directly. [Official discovery rules](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

Setup is complete. Re-run `/setup-matt-pocock-skills` only when intentionally
changing tracker, label or documentation conventions; the setup docs capture
the approved choices.

Useful workflows:

- `/to-spec`: turn an agreed conversation into a GitHub specification issue.
- `/to-tickets`: propose verifiable vertical slices and publish the agreed
  breakdown with native dependencies.
- `/triage`: clarify and label incoming work using the configured roles.
- `/implement` or `/implement-spec`: work a ticket or the unblocked ticket graph
  with focused verification and code review.

Follow `docs/agents/issue-tracker.md`, `triage-labels.md` and `domain.md` for this
repo's conventions. Existing user decisions remain resolved; the skills do not
make the founder transcribe songs or repeat setup questions for ordinary work.

Work-request and bug issue forms are versioned under `.github/ISSUE_TEMPLATE/`.
GitHub displays them once the files reach the default branch. Live tickets,
labels and native dependencies already work independently of that merge.
[GitHub's issue-form activation rules](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates).

## Updates

Keep this revision pinned during work. When an update is requested, inspect the
upstream diff, install the desired revision into a temporary directory using
the skill-installer helper, compare the installed files, then replace the
reviewed copies and regenerate the hash manifest. Preserve the upstream MIT
licence and any project-specific configuration. Reinstalling a global plugin
alongside these copies would duplicate skill entries; choose one installation
method for this repo.
