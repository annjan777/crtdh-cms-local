# Contact form privacy notice (copy for the frontend lane)

Status: engineering draft, **not legal advice**. The wording needs sign-off from the centre head and the institute's legal or data-protection contact before launch (see "Open questions"). The DPDP Act's substantive duties commence on 13 May 2027; we build to them now.

Assessment record: `.dpdp/assessment.yaml` (scope: the public contact form only).

## Where it goes
- **Short notice**: directly above the Send button of the contact form, always visible (not behind a toggle). No checkbox: the lawful ground is the person's own voluntary message for a stated purpose (DPDP Act s.7(a)), not consent, so a consent tick box would be misleading.
- **Full notice**: a "How we use your message" section on the Contact page (anchor `#privacy`), linked from the short notice and from the site footer.
- Both in English first. Hindi and Bengali versions are a decision for the centre (open question Q-03).

## Short notice (above the Send button)

> We use your name, email, phone (if you give it) and message only to reply to you. Messages are deleted after 12 months. [How we use your message](#privacy)

## Full notice (Contact page, `#privacy`)

> ### How we use your message
>
> **Who we are.** This form is run by the Common Research & Technology Development Hub (CRTDH), IIT Kharagpur. [confirm the exact name used on the site]
>
> **What we collect.** Your name, email address, phone number (optional) and the text of your message. We do not use cookies or tracking on this form. To block spam, Cloudflare Turnstile checks that the form was sent by a person; Cloudflare processes technical data such as your IP address for that check.
>
> **Maps and videos.** The map and the videos on this site come from Google Maps and YouTube. Nothing is loaded from them until you press "Show the map" or "Watch"; from then on Google receives your IP address and browser details, as for any visit to its sites.
>
> **Why.** Only to read and answer your enquiry. We do not add you to a mailing list, sell or share your details, or use them for anything else.
>
> **Who can see it.** A small number of CRTDH staff who answer enquiries, through our private content system. We receive a short email alert that a message has arrived; the alert does not contain your details.
>
> **How long we keep it.** Messages are deleted automatically 12 months after they are sent. If you want yours deleted earlier, or want to correct it, write to the contact below.
>
> **Your choices.** You can ask us what we hold about you, ask us to correct or delete it, or ask us to stop using it. Write to **[contact name, role]** at **[contact email]**. We reply within **30 days**. If you are not satisfied with our reply, you can complain to the Data Protection Board of India.
>
> *Last updated: [date of publication].*

## Placeholders the content owner must fill
- `[contact name, role]` and `[contact email]`: a named person or role at CRTDH who answers privacy questions (DPDP Act s.8(9)). Use a role mailbox, not a personal address.
- `[date of publication]`.
- Keep "12 months" in step with `CONTACT_RETENTION_DAYS` (default 365).

## Retention rule (implemented)
- `python manage.py purge_contact_messages` deletes contact messages older than `CONTACT_RETENTION_DAYS` (default 365 days). Runs daily from the `housekeeping` service in `deploy/docker-compose.yml`.
- 12 months keeps the one-year minimum the DPDP Rules set for personal data and processing logs (Rules r.8(3)), then erases because the purpose (answering the enquiry) is served (Act s.8(7)).
- Earlier deletion on request: a Publisher or Admin deletes the message in the CMS (`DELETE /api/v1/contact-messages/<id>/`). Whether an on-request deletion inside the first year conflicts with r.8(3) is open question Q-02.

## Controls behind the notice (implemented)
- Collected fields are only those listed above; no IP address or user agent is stored with the message.
- Text is HTML-escaped and stripped of control characters before storage; length limits on every field.
- Rate limit 5 per minute per IP; Turnstile verification (required in production); honeypot field.
- Messages are readable only by the Publisher and Admin roles in the CMS (session + MFA), never by the public site or the snapshot.
- The notification email carries no personal data (only the message id).

## Open questions (need a human answer)
- **Q-01** Is s.7(a) (voluntarily provided for a specified purpose) the right ground for the contact form, rather than consent? Owner: institute legal / data-protection contact.
- **Q-02** IIT Kharagpur may be "State" under Article 12; if so, Act s.17(4) changes the erasure duty (s.8(7)). Also: may we delete on request inside the first year given Rules r.8(3)? Owner: legal.
- **Q-03** Which languages besides English to offer the notice in. Owner: centre head.
- **Q-04** Who is the published contact for privacy questions, and is a processor contract in place with the email provider and Cloudflare? Owner: centre head.
