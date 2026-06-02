# brex-skills

A collection of custom [Claude Code](https://claude.ai/code) skills. Skills extend Claude Code with slash commands that trigger specialized behaviors — think of them as saved instructions that activate on demand.

> **Note:** Skills only work in Claude Code (the CLI / desktop app). They do not work in claude.ai in a browser.

---

## Skills

| Skill | Command | What it does |
|---|---|---|
| **learn** | `/learn` | Pauses the current task to teach you a concept you just hit, then returns you to where you left off. Invoke bare (`/learn`) to have it infer from context, or with a topic (`/learn symlinks`). |
| **idea** | `/idea` | Takes a fuzzy idea or initiative and walks you through structured systems thinking to a phased, executable plan. Built for non-engineers. |
| **curriculum** | `/curriculum` | Builds a structured, adaptive learning curriculum for any topic — ELI5 through deep dive, with an assessment log that adapts future modules to your answers. |
| **unclose** | `/unclose` | Coaches responses for Podium's `#unclose-at-risk` Slack channel. Reviews threads, drafts replies, and gives feedback before you post. |
| **email-gamification** | `/email-gamification` | *(internal skill — see skill.md for details)* |

---

## Installation

> You'll need to open **Terminal** for the steps below. On a Mac, press **Command + Space**, type `Terminal`, and hit Enter.

**Step 1 — Download the skills to your computer.**

Copy and paste this entire block into Terminal, then hit Enter:

```bash
git clone https://github.com/brexankoerner-spec/brex-skills.git ~/dev/brex-skills
```

**Step 2 — Make sure the skills folder exists.**

```bash
mkdir -p ~/.claude/skills
```

**Step 3 — Connect each skill to Claude Code.**

Copy and paste this entire block at once, then hit Enter:

```bash
ln -s ~/dev/brex-skills/learn ~/.claude/skills/learn
ln -s ~/dev/brex-skills/idea ~/.claude/skills/idea
ln -s ~/dev/brex-skills/curriculum ~/.claude/skills/curriculum
ln -s ~/dev/brex-skills/unclose ~/.claude/skills/unclose
```

That's it. Open Claude Code and type `/learn`, `/idea`, `/curriculum`, or `/unclose` to use a skill.

---

## Staying up to date

When skills are updated, you need to pull the latest version from GitHub to your computer. Set this up once and it happens automatically forever.

**Pick the option that matches how you use Claude Code:**

---

### Option A — I use the Claude Code desktop app

This sets up a background task that checks for updates every hour, even when Terminal is closed.

Open Terminal and run these commands **one at a time**, hitting Enter after each:

**1. Create the auto-update file:**
```bash
cat > ~/Library/LaunchAgents/com.brexskills.gitpull.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.brexskills.gitpull</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd "$HOME/dev/brex-skills" && git pull --quiet</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/brexskills-update.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/brexskills-update.log</string>
</dict>
</plist>
EOF
```

**2. Tell macOS to start running it:**
```bash
launchctl load ~/Library/LaunchAgents/com.brexskills.gitpull.plist
```

Done. macOS will now pull updates automatically every hour in the background. You never need to touch this again.

---

### Option B — I use Claude Code in Terminal

Add one line to your shell config and it will silently pull updates every time you open a new Terminal window.

**1. Add the auto-update line:**
```bash
echo '(cd ~/dev/brex-skills && git pull --quiet 2>/dev/null &)' >> ~/.zshrc
```

**2. Apply the change to your current Terminal window:**
```bash
source ~/.zshrc
```

Done. Every new Terminal window will silently sync skills in the background.
