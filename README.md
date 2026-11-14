# Instagram username checker - revised generator

Upload these four files to the root of your GitHub repository:
- app.py
- requirements.txt
- render.yaml
- README.md

Then redeploy the Render service.

## New generation rule
- Starts with exactly 3 English letters and no punctuation.
- After 15 checks without a preliminary available result, advances to 3 letters plus 1 randomly placed `.` or `_`.
- After each further 15 checks without a preliminary available result, increases punctuation count by one.
- Always retains at least 3 English letters.
- Instagram usernames support periods and underscores, not hyphens.

## Important limitations
Instagram does not provide a public authoritative username-availability endpoint. HTTP 404 is only a preliminary signal, not proof that the username can be registered. A login wall, challenge, rate limit, or ambiguous response is shown as Unknown. This app does not bypass Instagram protections.
