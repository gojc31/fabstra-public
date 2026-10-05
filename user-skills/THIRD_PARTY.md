# Third-party skills and agents in user-skills/

The repo's CC BY 4.0 licence covers the original skills only. Each vendored skill keeps its upstream licence, shipped inside its own folder (LICENSE, plus NOTICE or ATTRIBUTION.md where the licence asks for one); the two agents' licence is agents/LICENSE. Keep those files with any copy.

| Skill or file | Upstream | Licence | Copyright | Modified locally |
| --- | --- | --- | --- | --- |
| grilling | https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling | MIT | Copyright (c) 2026 Matt Pocock | yes - local sections are marked `<!-- Local addition, not upstream mattpocock/skills. -->` |
| handoff | https://github.com/mattpocock/skills/tree/main/skills/productivity/handoff | MIT | Copyright (c) 2026 Matt Pocock | no - SKILL.md matches upstream commit 386d4ff719a7 |
| to-questionnaire | https://github.com/mattpocock/skills/tree/main/skills/productivity/to-questionnaire | MIT | Copyright (c) 2026 Matt Pocock | yes - wording edits in SKILL.md |
| wait-what | https://github.com/mattpocock/skills/tree/main/skills/productivity/wait-what | MIT | Copyright (c) 2026 Matt Pocock | yes - SKILL.md points at the project's CLAUDE.md |
| wizard | https://github.com/mattpocock/skills/tree/main/skills/engineering/wizard | MIT | Copyright (c) 2026 Matt Pocock | yes - SKILL.md (adds `disable-model-invocation`); template.sh matches upstream commit cb7db0eeb627 |
| writing-for-agents | https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents | MIT | Copyright (c) 2026 Matt Pocock | yes - see VENDORED.md |
| impeccable | https://github.com/pbakaus/impeccable | Apache-2.0 | Copyright 2025 Paul Bakaus | yes - see VENDORED.md and NOTICE |
| impeccable: reference/ios.md, reference/android.md | https://github.com/ehmo/platform-design-skills | MIT | Copyright (c) 2026 ehmo (credited in impeccable's upstream NOTICE.md) | distilled upstream by Impeccable; licence text in impeccable/NOTICE |
| hallmark | https://github.com/Nutlope/hallmark (skills/hallmark @ 13ac0ec7e148) | MIT | Copyright (c) 2026 Hallmark contributors | yes - see VENDORED.md |
| prompt-master | https://github.com/nidhinjs/prompt-master | MIT | Copyright (c) 2026 Nidhin Joseph Nelson | yes - see MODIFIED.md |
| doctor-plus | https://github.com/robonuggets/doctor-plus | CC BY 4.0 | RoboNuggets | yes - see ATTRIBUTION.md |
| agents/automation-governance-architect.md | https://github.com/msitarzewski/agency-agents (specialized/automation-governance-architect.md) | MIT | Copyright (c) 2025 AgentLand Contributors | yes - lightly edited |
| agents/engineering-frontend-developer.md | https://github.com/msitarzewski/agency-agents (engineering/engineering-frontend-developer.md) | MIT | Copyright (c) 2025 AgentLand Contributors | yes - heavily rewritten |
| brief, bro, careful, design-pass, speed-pass, triage | none - original work in this repo | CC BY 4.0 (repo LICENSE) | JC / gojc31 | n/a |

Licence texts were fetched from each upstream repo with `gh api repos/<owner>/<repo>/contents/LICENSE` and are kept in `_licenses/` so the export runs offline.
