# UAT run sheet: staff editor

Run type: [ ] Simulated (not a real staff member)   [ ] Real staff
Tester: ____________  Role: Editor   Date: ________   Environment: [ ] preprod [ ] staging [ ] production
Build (bottom of the CMS Help menu or the `crtdh-build` tag on the site): ________   Observer: ____________

You are a lab staff member who keeps the website up to date. You can change things, but a Publisher puts them
live. Use the text "UAT test – please ignore" wherever you type.

| # | What you do | You should see | Result | Notes |
|---|---|---|---|---|
| E1 **must** | Open the CMS address. Sign in with your username and password, then the 6-digit code from your phone app. | The CMS home with the list of website pages. Your name and "Editor" are shown. A wrong code says so in plain words and lets you try again. Auto: `test_cms_editor` login | [ ] Pass [ ] Fail | |
| E2 **must** | Open **Home**. Click the big headline on the first slide and change it. Wait two seconds. | "Saved · not live yet" appears near the field. You did not have to press a Save button. | [ ] Pass [ ] Fail | |
| E3 **must** | Click **Preview**. | The home page as visitors will see it, with your new headline. | [ ] Pass [ ] Fail | |
| E4 **must** | In a private browser window, open the public website home page. | The **old** headline. Your change is not live yet. Auto: `test_edit_hero_autosave_preview_not_live` | [ ] Pass [ ] Fail | |
| E5 | Back in the CMS, look at the bar at the bottom of the screen. | Something like "1 unpublished change on 1 page · Preview · Request review". There is **no** "Publish" button for you. | [ ] Pass [ ] Fail | |
| E6 **must** | Replace the photo of that slide: choose a photo from your computer that is at least 1600 pixels wide. Type a short description of the photo (alt text). | The new photo shows in the editor and in Preview. | [ ] Pass [ ] Fail | |
| E7 | Try the same with a small photo (for example one forwarded on WhatsApp). | A clear message that the photo is too small for the home page and how big it must be. Nothing is replaced. Auto: `test_hero_upload_rules` | [ ] Pass [ ] Fail | |
| E8 | Try to save a photo without a description. | You are asked for the description; the save does not go through without it. | [ ] Pass [ ] Fail | |
| E9 **must** | Open **Team**. Add a new person: name "UAT Test Person", a designation, a photo, and a category. | The person appears in Preview in the right group, with the photo. Long names wrap neatly. | [ ] Pass [ ] Fail | |
| E10 | Edit that person's name to something in Hindi or Bengali (e.g. "परीक्षण व्यक्ति"). Open Preview on a phone or narrow the window. | The name shows correctly, nothing spills off the card. | [ ] Pass [ ] Fail | |
| E11 | Open **Media**. Hide one existing news item or event (use **Hide**, not delete). | It disappears from Preview but stays in the CMS list marked hidden. You can unhide it. | [ ] Pass [ ] Fail | |
| E12 | Look for a way to **delete** an item. | Editors can't delete; the option is missing or explains that a Publisher must do it. | [ ] Pass [ ] Fail | |
| E13 | Open the same slide in two browser tabs. Change the headline in tab 1, then a different headline in tab 2. | Tab 2 says someone else changed it in the meantime and offers to reload. Tab 1's text is not lost. Auto: `test_stale_save_two_tabs` | [ ] Pass [ ] Fail | |
| E14 | Pick one of your changes and choose **Discard**. | It goes back to what the public site shows. Other changes stay. | [ ] Pass [ ] Fail | |
| E15 **must** | Click **Request review**. | The bar says "Waiting for review". (The Publisher gets an email — checked in the Publisher sheet, P2.) Auto: `test_editor_sees_request_review_and_publishers_are_emailed` | [ ] Pass [ ] Fail | |
| E16 | Leave the CMS idle until your sign-in expires (or sign out), then try to edit. | You're asked to sign in again; after signing in you're back where you were and nothing you'd saved is lost. | [ ] Pass [ ] Fail | |
| E17 | Ask yourself: were any words or buttons confusing? | (Write them down. Not a pass/fail step.) | — | |

**Clean-up (production only):** discard every "UAT test" change, or ask the Publisher to leave them unpublished
and discard them.

Questions the tester asked (observer fills in, word for word):

1.
2.
3.
