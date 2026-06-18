# Deploying the live demo

The live demo is a thin [Streamlit](https://streamlit.io) UI (`app.py`) over the
existing CLI logic in `PasswordGenerator.py`. It imports the real functions —
no security logic is duplicated. It is hosted free on **Streamlit Community Cloud**.

## Why Streamlit Community Cloud

The project is stateless Python with importable functions and no database, so a
Streamlit Community Cloud app is the right fit: it deploys straight from this
GitHub repo, needs no server config, and is free for public repos.

## Run it locally first

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (see the project README for push commands).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app** → **Deploy a public app from GitHub**.
4. Fill the form:
   - **Repository:** `MetaMaaz/Password-Generator`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** pick a slug, e.g. `secure-password-generator`
5. Click **Deploy**. First build takes ~1–2 minutes while it installs
   `requirements.txt`.
6. Copy the resulting URL (e.g. `https://secure-password-generator.streamlit.app`)
   and set it as the repo's **About → Website** field.

No secrets are required for the default demo. `app.py` sets safe environment
defaults at startup, so the app runs without a committed `.env`.

## Optional: configuration via secrets

All thresholds (strength cutoffs, attacker guess rate, HIBP endpoint, timeouts)
are read from environment variables with sane defaults baked into `app.py`. If
you ever want to override them on the host, add them under **App → Settings →
Secrets** in the Streamlit dashboard — never hard-code them and never read them
from user input. Example:

```toml
GUESSES_PER_SECOND = "10000000000"
HIBP_TIMEOUT_SECONDS = "4"
```

## Security notes for this public demo

This is an attacker-facing public surface, so the demo is hardened in `app.py`:

- **Breach check is OFF by default.** The HaveIBeenPwned lookup is opt-in via a
  toggle, so the demo does not silently proxy visitor traffic to HIBP. When
  enabled, only the first 5 chars of the SHA-1 hash leave the browser
  (k-anonymity) — the full hash never does.
- **No SSRF surface.** The only outbound request is to HIBP, and the existing
  `validate_hibp_url()` enforces HTTPS + a hostname allowlist. The demo never
  fetches a user-supplied URL.
- **Input caps.** Each character pool is capped at 32 and total length at 64 via
  bounded sliders, so no oversized inputs reach the generator.
- **Soft per-session rate limits.** Generations and live breach checks are
  capped per browser session, on top of the core module's existing 1.5s minimum
  interval between HIBP calls.
- **Read-only, nothing stored.** No clipboard access, no visitor-triggered file
  writes, and no password is persisted server-side.
- **Secrets via host only.** `.env` stays gitignored; any overrides go through
  the Streamlit secrets manager, never through the UI.
