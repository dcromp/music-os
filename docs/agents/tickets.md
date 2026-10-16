# GitHub ticket index

Published 16 October 2026 after approval of the eight-ticket breakdown. This
is an identity/dependency index; [GitHub Issues](https://github.com/dcromp/music-os/issues)
holds current state, assignees, acceptance evidence and comments.

| Ticket | Outcome | Prerequisite |
|---|---|---|
| [#2](https://github.com/dcromp/music-os/issues/2) | Finalize the ten-recording timing, rhythm and pitch checkpoint | None |
| [#3](https://github.com/dcromp/music-os/issues/3) | Check the first four recordings' audible changes and rhythm contrasts | [#2](https://github.com/dcromp/music-os/issues/2) |
| [#4](https://github.com/dcromp/music-os/issues/4) | Review accompaniment for Brown Eyed Girl, Creep and House of the Rising Sun | [#2](https://github.com/dcromp/music-os/issues/2) |
| [#5](https://github.com/dcromp/music-os/issues/5) | Review Wonderwall's capo-2 shapes, changes and section rhythms | [#2](https://github.com/dcromp/music-os/issues/2) |
| [#6](https://github.com/dcromp/music-os/issues/6) | Prepare separate riff arrangements for Seven Nation Army and Come As You Are | [#2](https://github.com/dcromp/music-os/issues/2) |
| [#7](https://github.com/dcromp/music-os/issues/7) | Publish a small reviewed practice pack with traceable arrangement status | [#3](https://github.com/dcromp/music-os/issues/3) |
| [#8](https://github.com/dcromp/music-os/issues/8) | Run ordinary guitar practice and measure followability | [#7](https://github.com/dcromp/music-os/issues/7) |
| [#9](https://github.com/dcromp/music-os/issues/9) | Specify one permitted end-to-end launch-content route and its cost gaps | None |

The diagnostic checkpoint (#2) is closed with commit `4898704` as evidence.
Its dependent review tickets retain the completed prerequisite relationship;
they have no open baseline blocker. #7 depends only on #3, with the other
reviews supplying optional wider coverage. #8 is optional founder practice
after #7, without a transcription task. #9 can proceed in parallel.

Use the five approved triage roles. A claimed assignee indicates work in
progress; native open dependencies indicate blocked work. Close tickets only
when their acceptance criteria have evidence. Musical observation and model
agreement remain separate from independent recording acceptance.

```sh
gh issue list --repo dcromp/music-os --state open \
  --search "label:ready-for-agent no:assignee -is:blocked" \
  --json number,title,url
```

The [setup snapshot](github-setup.json) preserves initial issue identities and
the six native dependency edges; it is not a second live task tracker.
Workflow details are in [issue-tracker.md](issue-tracker.md).
