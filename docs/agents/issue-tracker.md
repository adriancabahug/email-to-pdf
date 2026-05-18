# Issue Tracker

**Type:** Local markdown

**Location:** `.scratch/` directory in the repo root

## Workflow

Issues are tracked as markdown files under `.scratch/`:

```
.scratch/
├── multi-account-search/
│   ├── 001-get-all-accounts.md
│   ├── 002-recursive-folders.md
│   └── ...
```

## Naming Convention

- Directory name: feature or component name (kebab-case)
- File name: `<number>-<short-description>.md`
- Numbering should follow the dependency order (blockers first)

## Creating Issues

Create a markdown file with:

```markdown
# Issue Title

## Description
Detailed description of what needs to be built.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

## References

Skills using this tracker:
- `to-issues` - creates issues from plans
- `to-prd` - creates PRDs
- `grill-me` - uses issues for planning