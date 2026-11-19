# Remediation status: CRTDH CMS v3 (2026-11-20)

Branch `v3/remediation`, 18 commits on top of `1f29d21`. Not pushed or deployed. Evidence: TEST-RESULTS.md and CODE-CHANGES.md.
**Decision: still not production-ready** until the owner and CIC items below are done (PRODUCTION-CHECKLIST.md). The code side is ready for a controlled staging rollout.

| R | F | Status | Evidence / what changed | Remaining |
|---|---|---|---|---|
| R-1 | F-01 MFA | **OWNER ACTION REQUIRED** (code: VERIFIED FIX) | Existing MFA, recovery and OAuth gate verified by tests. Gap fixed: a password-only session no longer survives switching MFA on (05e20b8, 3 tests that fail on old code). | Set `MFA_ENABLED=True`, enrol users, disconnect old Claude connections. |
| R-2 | F-02 creds | **OWNER + CIC ACTION REQUIRED** | Rotation steps and kill-checks in the checklist (§2). | Rotate Claude secret, admin passwords, CIC SFTP. |
| R-3 | F-03 backups | **OWNER ACTION REQUIRED** (tooling: VERIFIED) | `deploy/backup/` backup + restore-check, 13/13 incl. real restore on a disposable DB. | Install on the lab server, run restore-check, add cron, add off-host copy. |
| R-4 | F-04 prod infra | **CIC ACTION REQUIRED** | Checklist §4–§6. Not resolved by staging. | All of it. |
| R-5 | F-05 notice | **FIXED — TESTS PENDING** + OWNER ACTION | Real cause: the worker image never contained the notice file; the footer link was lost in the old-design port. Both fixed (385f217); local build shows `#privacy` and the footer link. | Staging rebuild + publish to confirm. Grievance contact still needed (left out until given). |
| R-6 | F-08 E2E | **VERIFIED FIX** | Restore spec read the wrong key and depended on test order; rehearsal ran without MFA; golden headings out of date; axe library missing. Full E2E 208/208 on wiped state. | — |
| R-7 | F-07 false warning | **VERIFIED FIX** | Reproduced: leftover browser draft from "Leave anyway". Fixed plus a Discard button (f5acd2c); 4 tests. | — |
| R-8 | F-06 embeds | **VERIFIED FIX** + OWNER ACTION | Click-to-load map and video restored (930dcee); test: 0 Google/YouTube requests on load on 12 pages. Notice updated. | Turn off Cloudflare Web Analytics. |
| R-9 | F-09 test seeds | **VERIFIED FIX** | Guards existed and are now locked by tests; harness repr hides seeds; new logs scan clean. History not rewritten (needs your approval). | Optional history rewrite. |
| R-10/R-12 | F-10 email obfuscation | **OWNER ACTION REQUIRED** | Cloudflare zone setting (checklist §6). | Turn it off. |
| R-11 | F-11 containers | **FIXED — TESTS PENDING** | Agent image non-root by default; compose already non-root and read-only; sftp root justified; Trivy CI job; digest-pin script. | Build images; run the script; first CI run. |
| R-13 | — uptime | **OWNER ACTION REQUIRED** | Spec in checklist §8. | Set up and test the alerts. |
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
| F-18 (low) | Restored design has fewer headings (Facilities 25→4, Services 8→2, Social impact 3→1): weaker screen-reader navigation | **OPEN**: design decision for you |
| F-19 (low) | An 8192 px photo in the "Jio" gallery is served as-is (page weight) | **OWNER ACTION** (re-export at about 2400 px) |
| F-20 | Footer dark against light header; invisible footer logo; justified short text | **VERIFIED FIX** (your feedback, 87a695c/2356230) |
| F-21 | Home hero rendered an empty `<img>` for a slide without a photo | **VERIFIED FIX** (be95d37) |
| F-22 | Home "Get Directions" opened the map embed, not directions | **VERIFIED FIX** (930dcee) |
