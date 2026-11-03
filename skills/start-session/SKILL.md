---
name: start-session
description: Load the user's settings and orient yourself at the start of every session.
when-to-use: First thing in every session, and again whenever SETTINGS.md changes.
---

# Start a session

1. Run `uv run tutor start` and read its entire output.
2. If it prints `ONBOARDING REQUIRED`, switch to `skills/onboarding/SKILL.md` now. Don't start on
   the user's request until onboarding is done.
3. Otherwise, take in from SETTINGS.md:
   - who the reader is (`audience`): pick vocabulary, depth and analogies for that person;
   - the writing `language`;
   - the free-text preferences (explanation style, notation, past confusions).
4. Check the topic list it printed. If the user's request matches an existing topic, continue
   in that topic (`skills/learn-more`). Otherwise propose a new one (`skills/new-topic`).
5. If any `tutor` command later says `SETTINGS NOT READ`, run step 1 again.
