# Triage Labels

## Canonical Vocabulary

| Label | Description |
|-------|--------------|
| `needs-triage` | Maintainer needs to evaluate - issue is new or needs initial review |
| `needs-info` | Waiting on reporter - need more information before proceeding |
| `ready-for-agent` | Fully specified, AFK-ready - an agent can pick it up with no human context |
| `ready-for-human` | Needs human implementation - requires human decision or work |
| `wontfix` | Will not be actioned - rejected or not planned |

## Usage Notes

- These are the canonical labels - do not create duplicates or variations
- The `triage` skill manages moving issues through these states
- Other skills like `to-issues` apply `ready-for-agent` automatically

## File Format

When using local markdown, add labels as YAML frontmatter:

```yaml
---
labels: [ready-for-agent]
---
```