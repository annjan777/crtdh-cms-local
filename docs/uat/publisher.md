# UAT run sheet: publisher

Run type: [ ] Simulated (not a real staff member)   [ ] Real staff
Tester: ____________  Role: Publisher   Date: ________   Environment: [ ] preprod [ ] staging (never production for P4–P9)
Build: ________   Observer: ____________

You check what editors (and Claude) changed and put it live. Run the Editor sheet first, so there are
changes waiting, or ask someone to make two or three "UAT test" changes.

| # | What you do | You should see | Result | Notes |
|---|---|---|---|---|
| P1 **must** | Sign in with password and 6-digit code. | The CMS with your name and "Publisher". | [ ] Pass [ ] Fail | |
| P2 **must** | Check your email. | One email saying an editor asked for a review, with a link to the review screen. | [ ] Pass [ ] Fail | |
| P3 **must** | Open **Review & publish**. | All unpublished changes grouped by page. For each: what changed (old → new), who changed it, when, and whether it came from the CMS or from Claude. Auto: `test_publisher_sees_review_and_publish` | [ ] Pass [ ] Fail | |
| P4 **must** | Discard one change you don't want to go live. Then click **Publish**. | Progress you can follow: Queued → Building → Uploading → "Live at hh:mm". It takes a few minutes. Auto: `test_edit_preview_publish_static_changed` | [ ] Pass [ ] Fail | |
| P5 **must** | Open the public website in a private window (refresh). | The published changes are there. The discarded one is not. | [ ] Pass [ ] Fail | |
| P6 | Click **Publish** twice quickly (make one small change first). | Only one publish runs; the second click shows the one already running. Auto: `test_double_click_publish_one_build` | [ ] Pass [ ] Fail | |
| P7 | With nothing changed, open Review & publish. | "Nothing to publish". | [ ] Pass [ ] Fail | |
| P8 | (Rehearsal: the developer stops the upload machine first.) Make a change and publish. | "Waiting for upload machine (last seen hh:mm)" — not a false "Live". When it is back, the publish continues. Auto: `test_agent_offline_shows_waiting` | [ ] Pass [ ] Fail | |
| P9 | (Rehearsal: the developer makes the upload fail.) Publish. | A failure message that names the step, gives a reason and says **the site is unchanged**. The public site still shows the previous version. | [ ] Pass [ ] Fail | |
| P10 **must** | Open **History**. Pick an earlier published version and choose **Restore**. | A confirmation naming that version and its date. After confirming, its content comes back as unpublished changes (nothing goes live until you publish). Auto: `test_restore_version_confirmation_creates_draft` | [ ] Pass [ ] Fail | |
| P11 | Delete one "UAT test" item. | A confirmation that names the item. After confirming it is gone from Preview. | [ ] Pass [ ] Fail | |
| P12 | Open **Messages** (contact form). Send a message from the public Contact page first. | Your message is listed with name, email and text; any HTML in it shows as plain text. | [ ] Pass [ ] Fail | |
| P13 | Look for user management. | Publishers can't add users or change roles (only the Admin can). | [ ] Pass [ ] Fail | |
| P14 | Were any words, states or buttons confusing? | (Write them down.) | — | |

Questions the tester asked (observer fills in):

1.
2.
