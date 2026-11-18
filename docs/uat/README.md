# User acceptance tests (UAT)

Plain-language checks that the people who will run the website can do their jobs with the new CMS.
Three run sheets:

| Sheet | Who runs it | Time |
|---|---|---|
| [editor.md](editor.md) | a lab staff member with the **Editor** role | ~30 min |
| [publisher.md](publisher.md) | a staff member with the **Publisher** role | ~30 min |
| [connect-claude-timing.md](connect-claude-timing.md) | one non-developer, timed, nobody helping | 5 min target |

## Simulated or real: always say which

Every run sheet starts with a **Run type** box. Tick exactly one:

- **Simulated** — run by the QA agent or by a developer pretending to be staff, usually against the preprod
  rehearsal (`scripts/preprod.sh up`). It proves the steps *work*. It does **not** prove staff can do them
  without help, understand the wording, or find the buttons. Most steps are also covered by Playwright
  (`tests/e2e`), listed per step as "Auto:".
- **Real staff** — run by the actual person who will do this job, on staging or production, with the developer
  watching and **not helping** (write down every question they ask instead). Only real-staff runs count for
  sign-off.

A simulated pass is never reported as UAT sign-off. The final UAT report lists simulated and real runs in
separate tables.

## How to run a sheet

1. Print the sheet or copy it into a doc. Fill in the header (name, date, environment, build).
2. Do each step as written. Compare what you see with **You should see**.
3. Tick **Pass** or **Fail**. On Fail, write what you saw in **Notes** (a screenshot helps).
4. Don't skip a failed step's later steps unless they depend on it; mark those **Blocked**.
5. Hand the sheet to the developer. Each Fail becomes an issue with the step number (e.g. `UAT E4`).

## Test data

Rehearsal users (preprod / staging only, created by `seed_test_users --rehearsal`):
`erin_editor` (Editor), `priya` (Publisher), `adam_admin` (Admin). Their password and 6-digit-code secrets are in
`.preprod/users.json` / `.preprod/env` on the rehearsal machine, never in this document. On production, staff
use their own accounts.

Use obviously test-only text (e.g. "UAT test – please ignore") and discard or revert it at the end.
**Never publish test text on production**; publisher scenarios that publish are run on staging or preprod.

## Sign-off

| Sheet | Run type | Tester (role) | Date | Environment | Result | Open issues |
|---|---|---|---|---|---|---|
| Editor | | | | | | |
| Publisher | | | | | | |
| Connect Claude | | | | | | |

UAT passes when each sheet has one **real-staff** run with no open Fail in a step marked **must**.
