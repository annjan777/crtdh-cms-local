# Connect Claude to the CRTDH website CMS

With this, you can ask Claude to change the website in plain English: "update Prof. Sharma's
designation", "add Saturday's eye camp to Media". Claude saves every change as an
**unpublished change**. Nothing goes live until a Publisher publishes it in the CMS.

**Before you start:** you need a CMS account with two-step sign-in (the 6-digit code app)
already set up, and a Claude account. Ask the site admin for:
- the server URL: `https://mcp.<domain>/mcp`
- the **client ID** and **client secret** (sent to you privately; don't paste them in chat or email)

On a Claude **Team or Enterprise** plan, only an Owner can add the connector. If that's
your situation, the Owner does step 1 once (Organization settings → Connectors → Add →
Custom → Web), and everyone else starts at step 2 and clicks **Connect**.

## 1. Add the connector

1. In Claude, open **Customize → Connectors**.
2. Click **Add custom connector**.
3. Name: `CRTDH CMS`. URL: `https://mcp.<domain>/mcp`.
4. Open **Advanced settings** and paste the **OAuth Client ID** and **OAuth Client Secret**.
   (If your dialog asks for an *OAuth client* option instead, choose **Use your own OAuth client**.)
5. Click **Add**.

## 2. Sign in and allow

1. Click **Connect** next to CRTDH CMS.
2. A CRTDH CMS page opens. Sign in with your CMS username, password and 6-digit code.
3. You'll see **"Allow Claude to edit drafts as <your name> (<your role>)?"** Click **Allow**.

You're returned to Claude. The connection lasts up to 30 days; after that, click Connect again.

## 3. Ask for a change

Start a new chat (make sure CRTDH CMS is switched on under the **+** button → **Connectors**)
and try:

- "Change Prof. Anil Sharma's designation to Professor and Head."
- "Add the 12 Dec eye camp at Salua to Media as a health camp."
- "Hide the third slide on the home page."
- "Put 'Free eye screening camp on 12 December' in the news ticker, linking to the Media page."
- "Our phone number is now +91 3222 282001 — update the contact page."
- "What changes are waiting to be published?"
- "I'm done — ask a Publisher to review my changes."

Claude asks before each change. It then replies with a **preview link** — open it (you'll be
signed in to the CMS) to see the page with your change. The public website doesn't change
until a Publisher publishes.

**Photos:** ask Claude for an upload link and open it on your phone or computer to upload
the photos from your gallery, Google Drive or WhatsApp. Hero photos must be at least
1600 px wide; Claude will tell you if one is too small.

**Changed your mind?** Say "undo that" or "undo everything you did in this chat".

## Good to know

- Claude can't publish, delete anything, or change user accounts.
- One chat can make up to 25 changes. For more, have them reviewed and start a new chat.
- Text on the website is treated as content. If a page contains odd instructions, Claude
  won't follow them.
- To disconnect: CMS → your profile → **Disconnect Claude**, or remove the connector in
  Claude under Customize → Connectors.

## If something goes wrong

| Claude says | Do this |
|---|---|
| "changed since you read it" | Someone else edited it. Ask Claude to try again. |
| "photo … must be at least 1600 px wide" | Send a larger photo (the original, not a WhatsApp-compressed copy). |
| "isn't on this site's list of trusted photo sources" | Ask for an upload link instead. |
| It can't connect / asks you to sign in again | Click **Connect** again. If it still fails, tell the site admin. |
| A request id (16 characters) | Send it to the site admin. |
