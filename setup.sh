#!/bin/bash
# One-time setup for a new machine after cloning this repo.
#
#   git clone https://github.com/brexankoerner-spec/brex-skills.git ~/dev/brex-skills
#   cd ~/dev/brex-skills && ./setup.sh
#
# What this does:
#   1. Symlinks every skill directory into ~/.claude/skills/ so Claude Code sees them.
#
# What this does NOT do (intentionally excluded from this repo/script):
#   - The email-scorecard launchd plists and their backing script are not
#     version-controlled here (the script has a live Slack bot token). Set
#     that automation up manually on any machine that needs it.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

# Directories in this repo that are skills (i.e. not plain config/asset dirs).
EXCLUDE_DIRS=(".git" ".claude")

echo "== Symlinking skills into $SKILLS_DIR =="
mkdir -p "$SKILLS_DIR"
for dir in "$REPO_DIR"/*/; do
  name="$(basename "$dir")"

  skip=false
  for excluded in "${EXCLUDE_DIRS[@]}"; do
    [[ "$name" == "$excluded" ]] && skip=true && break
  done
  $skip && continue

  target="$SKILLS_DIR/$name"
  if [[ -L "$target" ]]; then
    echo "  - $name already linked, skipping"
  elif [[ -e "$target" ]]; then
    echo "  ! $target exists and is not a symlink — skipping (resolve manually)"
  else
    ln -s "$REPO_DIR/$name" "$target"
    echo "  + linked $name"
  fi
done

echo
echo "== Done =="
echo "Note: email-scorecard automation (launchd plists + script) is not part"
echo "of this repo and must be set up manually if needed on this machine."
