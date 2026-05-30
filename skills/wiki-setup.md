---
name: wiki-setup
description: Step-by-step installation of ai-wiki-system. Rigid skill — follow every step in order without skipping.
type: rigid
---

# Wiki Setup — Guided Installation

> **This is a local skill file.**
> Access it with `Read skills/wiki-setup.md` — do NOT call a Skill tool.

**IMPORTANT: This is a rigid skill. Execute every step in the order shown. Do not skip or reorder.**

## Pre-check: identify your platform

- [ ] You are on **OpenClaw** → follow §openclaw

---

## §openclaw — Setup for OpenClaw

### Step OC-1: Verify Python dependencies

Same as CC-1.

### Step OC-2: Create wiki.config.json

Same as CC-2.

### Step OC-3: Build the plugin

```bash
cd plugins/wiki-context-plugin
npm install
npm run build
```

### Step OC-4: Configure the plugin in OpenClaw

```bash
py scripts/setup_openclaw.py --workspace <WORKSPACE>
```

If auto-detection fails:
```bash
py scripts/setup_openclaw.py --workspace <WORKSPACE> --config <OPENCLAW_CONFIG_PATH>
```

Verify that `pythonExecutable` in the OpenClaw config is the absolute path:
```bash
py -c "import sys; print(sys.executable)"
```

### Step OC-5: Initialize LanceDB

Same as CC-4.

### Step OC-6: Update your user AGENTS.md

Open `AGENTS.md` of your project (or create `~/.openclaw/AGENTS.md`) and add:

```markdown
## Wiki workspace
Active wiki workspace: <WORKSPACE>
```

### Step OC-7: Restart OpenClaw

**OpenClaw setup complete.**
