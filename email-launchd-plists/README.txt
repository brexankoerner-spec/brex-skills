Email Scorecard — Paused launchd Agents
========================================

These are the local Mac scheduler (launchd) config files for the Email
Gamification feature. When active, they fire Claude Code sessions at 8am,
10am, 12pm, 2pm, and 4pm on weekdays to scan Gmail, score emails by urgency,
and post a prioritized inbox scorecard to Slack.

They were moved here on 2026-06-17 to pause the feature without losing the
config. They will NOT run while stored here.


TO REACTIVATE
-------------
Run this in Terminal:

  cp ~/dev/brex-skills/email-launchd-plists/*.plist ~/Library/LaunchAgents/ && for f in ~/Library/LaunchAgents/com.brexan.email-scorecard-*.plist; do launchctl load "$f"; done

That copies them back into the auto-load folder and starts them immediately.


TO PAUSE AGAIN
--------------
Run this in Terminal:

  for job in com.brexan.email-scorecard-8am com.brexan.email-scorecard-10am com.brexan.email-scorecard-12pm com.brexan.email-scorecard-2pm com.brexan.email-scorecard-4pm; do launchctl unload ~/Library/LaunchAgents/${job}.plist; done && mv ~/Library/LaunchAgents/com.brexan.email-scorecard-*.plist ~/dev/brex-skills/email-launchd-plists/
