# UAT: the 5-minute "Connect Claude" test

Goal (PLAN WS4.7): a non-developer goes from **"I have a CMS account with the 6-digit code set up"** to **"I can
see Claude's change in Preview"** in **5 minutes or less**, using only `docs/connect-claude.md`.

Run type: [ ] Simulated (developer or agent; does NOT count)   [ ] Real staff (counts)
Tester: ____________ (not a developer, has not seen the guide before)   Date: ________
Claude plan: [ ] Free/Pro/Max  [ ] Team/Enterprise (an Owner added the connector beforehand: [ ] yes)
Environment: [ ] staging [ ] production MCP hostname: ______________   Device: [ ] laptop [ ] phone
Observer: ____________ with a stopwatch

**Before the clock starts (not timed):** the tester's CMS account exists and has two-step sign-in set up; they
have a Claude account and are signed in at claude.ai; they have received the server URL and the client
ID/secret privately; the guide is open.

**Rules for the observer:** start the stopwatch when the tester opens the guide. Do not help. Don't point.
If the tester is stuck for 60 seconds, write down where and what they said, then give the smallest possible
hint and mark that step **Helped**. Stop the clock when the change is visible in Preview.

| # | Tester does | Should see | Time (mm:ss) | Result | Where they hesitated / what they said |
|---|---|---|---|---|---|
| C1 | Opens Claude → Customize → Connectors → Add custom connector | The add-connector dialog | | [ ] Pass [ ] Fail [ ] Helped | |
| C2 | Enters name, server URL, and (Advanced settings) the client ID and secret; clicks Add | "CRTDH CMS" in the connector list | | [ ] Pass [ ] Fail [ ] Helped | |
| C3 | Clicks Connect | A CRTDH CMS sign-in page opens | | [ ] Pass [ ] Fail [ ] Helped | |
| C4 | Signs in with username, password, 6-digit code | "Allow Claude to edit drafts as <name> (<role>)?" | | [ ] Pass [ ] Fail [ ] Helped | |
| C5 | Clicks Allow | Back in Claude, connector shows as connected | | [ ] Pass [ ] Fail [ ] Helped | |
| C6 | New chat, connector switched on. Types: "Change the first home slide's headline to 'UAT test – please ignore'" | Claude asks to confirm, then says it was saved as a draft and gives a preview link; it says it is not live yet | | [ ] Pass [ ] Fail [ ] Helped | |
| C7 | Opens the preview link | The home page with the new headline (signed in to the CMS) | **stop clock** | [ ] Pass [ ] Fail [ ] Helped | |
| C8 | (not timed) Opens the public site in a private window | The old headline: nothing went live | | [ ] Pass [ ] Fail | |
| C9 | (not timed) Asks Claude "undo that" | Claude discards its change; Preview shows the old headline again | | [ ] Pass [ ] Fail | |

**Total time C1→C7:** ____ min ____ s    **Pass if ≤ 5:00 with no Helped step.**   Result: [ ] PASS  [ ] FAIL

If it fails, the fix goes into the guide or the product (not into "train the user"): note which step took
longest and why.

## What can and cannot be simulated

- The sandbox has no route from Anthropic's cloud to our server and no claude.ai account, so **C1, C2, C5, C6 can
  only run for real** (needs the public MCP hostname chosen in gate item d5).
- Simulated coverage: `tests/e2e/test_mcp_connector.py` drives the OAuth sign-in (C3–C4 consent text, TOTP,
  PKCE) and calls the same MCP tools Claude would (find → update → preview link → not live → undo). It proves
  the server side works; it says nothing about the 5-minute target.
