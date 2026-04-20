# Contract 04: Memory Manifest

**Status**: Canonical  
**Last updated against spec version**: 0.1.0  
**Schema version**: 1

## manifest.json

Located at `~/.nativeagents/memory/manifest.json`.

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-19T14:30:00Z",
  "total_token_budget": 4096,
  "files": [
    {
      "path": "core/user.md",
      "name": "Who — core user identity",
      "description": "Top-level facts",
      "category": "core",
      "token_budget": 400,
      "write_protected": false,
      "created_at": "2026-03-15T09:00:00Z",
      "updated_at": "2026-04-18T22:00:00Z",
      "tags": ["identity"],
      "extra": {}
    }
  ]
}
```

## File frontmatter

Each memory file is Markdown with YAML frontmatter:

```markdown
---
name: Who — core user identity
description: Top-level facts
category: core
token_budget: 400
write_protected: false
created_at: 2026-03-15T09:00:00Z
updated_at: 2026-04-18T22:00:00Z
tags: [identity]
---

## Content
```

## Categories (suggested, not enforced)

`core`, `relationship`, `projects`, `procedures`, `working`, `reference`

Unknown categories MUST be tolerated for forward compatibility.
