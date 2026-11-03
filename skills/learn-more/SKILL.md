---
name: learn-more
description: Extend an existing tutorial when the user asks a follow-up or wants to go deeper, keeping abstract/intro/contents/glossary consistent.
when-to-use: "Explain X more", "why does Y happen?", "add a section on Z", or confusion about something already written.
---

# Learn more

1. **Find where it belongs.** Read `topic.yaml` and the current pages. Decide:
   - clarify an existing passage (the user was confused): rewrite it in place;
   - a new sub-question: add a subsection in `contents.md`;
   - a large side topic: a new page (e.g. `appendix-<name>.md`) plus `uv run tutor order <topic> --set ...`.
2. **If the user was confused, find out why before rewriting.** Check: a term they didn't know,
   a skipped step, a missing example, or a bad analogy. Fix that cause. If it reveals something
   durable about the reader, offer to record it (see `skills/onboarding`, step 3).
3. **Write** following `skills/clear-writing` and `skills/explain-math`.
4. **Reconcile the paper (mandatory, same turn):**
   - `intro.md`: does the roadmap list every section that now exists? Have the prerequisites changed?
   - `abstract.md`: does the summary cover the new material? Remove claims about content that was
     cut.
   - `glossary.md`: is there an entry for each newly defined term? Are changed meanings updated
     and terms that are no longer used removed?
   - `topic.yaml`: is `order` right? (`glossary.md` stays last unless the user wants otherwise.)
5. **Check understanding.** Ask one short question, or ask the user to restate the new idea.
6. **End of turn:** `skills/readability-review`, then `uv run tutor lint <topic>`.
