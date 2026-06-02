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

Each skill is a folder. Symlink the ones you want into `~/.claude/skills/`:

```bash
# Clone the repo
git clone https://github.com/brexankoerner-spec/brex-skills.git ~/dev/brex-skills

# Symlink a skill (repeat for each one you want)
ln -s ~/dev/brex-skills/learn ~/.claude/skills/learn
ln -s ~/dev/brex-skills/idea ~/.claude/skills/idea
ln -s ~/dev/brex-skills/curriculum ~/.claude/skills/curriculum
ln -s ~/dev/brex-skills/unclose ~/.claude/skills/unclose
```

Then use the skill in any Claude Code session with `/skill-name`.

---

## Staying up to date

Skills update when you pull the repo:

```bash
cd ~/dev/brex-skills && git pull
```

No need to re-symlink — the symlink points to the folder, so updates are live immediately.
