# Remediation status: CRTDH CMS v3 (2026-11-20)

Branch `v3/remediation`, 22 commits on top of `1f29d21`. Updated with the owner's decisions of 2026-11-20 02:41. Not pushed or deployed. Evidence: TEST-RESULTS.md and CODE-CHANGES.md.
**Code: ready for a controlled release.** Production readiness now depends on tomorrow's server setup and checks (PRODUCTION-CHECKLIST.md §1–§3); the remaining risks are owner-accepted and recorded.

| R | F | Status | Evidence / what changed | Remaining |
|---|---|---|---|---|
| R-1 | F-01 MFA | **RISK ACCEPTED BY OWNER** (MFA off) | Code verified and kept switchable; the switch-over gap is fixed (05e20b8) in case MFA is turned on later. | Strong, unique admin passwords. |
| R-2 | F-02 creds | **OWNER ACTION REQUIRED** (Claude secret, admin passwords) / **RISK ACCEPTED** (CIC SFTP password) | Checklist §3. | Rotate the Claude secret; strong admin passwords. |
| R-3 | F-03 backups | **VERIFIED FIX** (owner's design) | Backup page: Admins download content or content + photos and upload to roll back as unpublished changes (c18f02c); 18 backend + 5 admin + 1 real-stack E2E tests. Server cron scripts removed. | First full backup downloaded after go-live (checklist §2). |
| R-4 | F-04 prod infra | **CIC ACTION REQUIRED** | Checklist §4–§6. Not resolved by staging. | All of it. |
| R-5 | F-05 notice | **FIXED — TESTS PENDING** + OWNER ACTION | Real cause: the worker image never contained the notice file; the footer link was lost in the old-design port. Both fixed (385f217); local build shows `#privacy` and the footer link. | Staging rebuild + publish to confirm. Grievance contact still needed (left out until given). |
| R-6 | F-08 E2E | **VERIFIED FIX** | Restore spec read the wrong key and depended on test order; rehearsal ran without MFA; golden headings out of date; axe library missing. Full E2E 208/208 on wiped state. | — |
| R-7 | F-07 false warning | **VERIFIED FIX** | Reproduced: leftover browser draft from "Leave anyway". Fixed plus a Discard button (f5acd2c); 4 tests. | — |
| R-8 | F-06 embeds | **VERIFIED FIX** + OWNER ACTION | Click-to-load map and video restored (930dcee); test: 0 Google/YouTube requests on load on 12 pages. Notice updated. | Turn off Cloudflare Web Analytics. |
| R-9 | F-09 test seeds | **VERIFIED FIX** | Guards existed and are now locked by tests; harness repr hides seeds; new logs scan clean. History not rewritten (needs your approval). | Optional history rewrite. |
| R-10/R-12 | F-10 email obfuscation | **OWNER ACTION REQUIRED** | Cloudflare zone setting (checklist §6). | Turn it off. |
| R-11 | F-11 containers | **FIXED — TESTS PENDING** | Agent image non-root by default; compose already non-root and read-only; sftp root justified; Trivy CI job; digest-pin script. | Build images; run the script; first CI run. |
| R-13 | — uptime | **RISK ACCEPTED BY OWNER** (no alerts) | — | — |
| R-14 | — contrast | **VERIFIED** (no change needed) | Measured: menu, footer and buttons ≥ 4.5:1 (lowest: active mobile item, 4.50 at 16 px). | — |
| R-15 | F-12 CSP | **VERIFIED FIX (partial by design)** | Inline `<style>` blocked; style attributes still allowed (React prerender needs them). 14 CSP tests (f50879b). | — |
| R-16 | F-13 http links | **OWNER ACTION REQUIRED** | Content, not code (seed edit reverted: seed must match live). | Fix in CMS → Media coverage; check the uniindia link by hand. |
| R-17 | F-14 dotfile 200 | **FIXED — TESTS PENDING** | Gateway 404 rule + test (7893674). | `nginx -t` + curl check on deploy. |
| R-17 | F-15 HMAC | **VERIFIED FIX** | Both sides sign the full path; backward compatible; tests. | — |
| — | F-16 Turnstile keys | **NOT APPLICABLE — WITH EVIDENCE** (code) | Fails closed without a secret (`turnstile.py`); staging uses test keys on purpose; contact form works (your 19 Nov check). | Real keys plus one real send in production. |

## Found during remediation
| ID | Finding | Status |
|---|---|---|
| F-17 | 8 of 57 admin browser tests already failed at 1f29d21 (the audit counted only the unit tests) | **VERIFIED FIX** (61/61) |
| F-18 (low) | Restored design had fewer headings | **VERIFIED FIX** (6876ca6): item names are headings again; pixel-identical at 1440 and 390 px |
| F-19 (low) | An 8192 px photo in the "Jio" gallery is served as-is (page weight) | **OWNER ACTION** (re-export at about 2400 px) |
| F-20 | Footer dark against light header; invisible footer logo; justified short text | **VERIFIED FIX** (your feedback, 87a695c/2356230) |
| F-21 | Home hero rendered an empty `<img>` for a slide without a photo | **VERIFIED FIX** (be95d37) |
| F-22 | Home "Get Directions" opened the map embed, not directions | **VERIFIED FIX** (930dcee) |
| F-23 | Unused code and dead "until merged" import fallbacks (a broken import would have silently disabled Claude-token revocation) | **VERIFIED FIX** (7f6cc2c): removed; lint 0 unused |
| F-24 | Committed E2E logs with test-user TOTP seeds still in the tree | **VERIFIED FIX** (7f6cc2c): removed from the tree; git history unchanged (rewrite needs your approval) |
