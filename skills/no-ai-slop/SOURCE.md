# Vendored skill

Source: https://github.com/petergyang/no-ai-slop (Peter Yang), MIT License, see LICENSE in this directory.

First vendored 2026-07-23. Re-based on upstream commit 000650b156983f5159695b441477f4e63b25dc85 (2026-10-16) on 2026-10-31, when the second-brain and common-ai copies were merged into one shared skill. `eval.md` is upstream's verbatim; `SKILL.md` is upstream plus the house sections "Scope: every medium", "Reader-cited tells", "Voice-mode tells" and "Structural slop", which are not in upstream.

Validated against monotykamary/Tom's published writing before adoption: its instructions match Tom's proven practice on concreteness, named sources, active voice, killing fake-profound kickers and summary-recap endings, and formatting restraint. It is stricter than Tom on binary contrasts and colon reveals (Tom uses them sparingly for genuine reframes; the skill allows this as voice) and on em dashes (Tom uses them freely; the house rule bans them, which wins). Use as the final editing pass for blog posts and social copy.

Maintenance: this directory is shared byte-for-byte with the common-ai repository (`scripts/shared-skills.txt` in the vault). The vault's `cog-update.sh` also lists `SKILL.md` here as an upstream COG file, so a framework update can overwrite it; `scripts/sync-shared-skills.sh status` reports that as drift.
