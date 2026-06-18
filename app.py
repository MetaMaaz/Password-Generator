"""
Live demo for the Password Generator.

This is a THIN Streamlit wrapper over the existing CLI logic in
PasswordGenerator.py — no security logic is reimplemented here. It imports
and calls the real functions (generate_password, get_strength,
calculate_entropy, time_to_crack, check_hibp).

Public-demo hardening lives in this file only:
  - sensible env defaults so no .env is needed on the host
  - input size caps (sliders are bounded; total length is clamped)
  - a soft per-session rate limit on generations and breach checks
  - the HaveIBeenPwned breach check is OFF by default (opt-in toggle)
  - no clipboard / no filesystem writes triggered by visitors
"""

import os
import time

# --- Provide safe defaults BEFORE importing the core module ----------------
# The core module reads these via os.getenv() at call time. Setting them here
# means the hosted demo needs no .env file committed to the repo.
_ENV_DEFAULTS = {
    "HIBP_URL": "https://api.pwnedpasswords.com/range",
    "HIBP_ALLOWED_DOMAIN": "api.pwnedpasswords.com",
    "HIBP_TIMEOUT_SECONDS": "5",
    "STRONG_MIN_LENGTH": "12",
    "STRONG_MIN_SYMBOLS": "2",
    "STRONG_MIN_NUMBERS": "2",
    "MEDIUM_MIN_LENGTH": "8",
    "MIN_PASSWORD_LENGTH": "4",
    "GUESSES_PER_SECOND": "1000000000",
    "AMBIGUOUS_CHARS": "0OolI1",
    "CLIPBOARD_CLEAR_SECONDS": "30",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)

import streamlit as st

# Import the REAL logic. Nothing below reimplements it.
from PasswordGenerator import (
    generate_password,
    get_strength,
    calculate_entropy,
    time_to_crack,
    check_hibp,
)

# --- Demo guardrails -------------------------------------------------------
MAX_PER_POOL = 32          # max letters / symbols / numbers each (slider cap)
MAX_TOTAL_LENGTH = 64      # hard cap on total password length
SESSION_GEN_LIMIT = 60     # soft cap: generations per browser session
SESSION_HIBP_LIMIT = 15    # soft cap: live breach checks per browser session

st.set_page_config(
    page_title="Secure Password Generator — Live Demo",
    page_icon="🔐",
    layout="centered",
)

# --- Clean security-tool theme (dark, minimal, monospace accents) ----------
st.markdown(
    """
    <style>
      .stApp { background: #0d1117; }
      .block-container { max-width: 760px; padding-top: 2.2rem; }
      h1, h2, h3 { color: #e6edf3; letter-spacing: -0.01em; }
      p, label, .stMarkdown { color: #adbac7; }
      .tl-tag {
        display:inline-block; font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
        color:#7ee787; border:1px solid #2ea04366; background:#2ea0431a;
        padding:2px 8px; border-radius:6px; margin-bottom:14px;
      }
      .tl-pw {
        font: 22px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
        color:#e6edf3; background:#161b22; border:1px solid #30363d;
        border-radius:10px; padding:16px 18px; word-break:break-all;
        user-select:all;
      }
      .tl-metric { background:#161b22; border:1px solid #30363d; border-radius:10px;
        padding:14px 16px; height:100%; }
      .tl-metric .k { font:12px ui-monospace,monospace; color:#768390; text-transform:uppercase;
        letter-spacing:.06em; }
      .tl-metric .v { font:20px ui-monospace,monospace; color:#e6edf3; margin-top:4px; }
      .badge { display:inline-block; padding:3px 12px; border-radius:999px;
        font:13px ui-monospace,monospace; font-weight:600; }
      .badge.Strong { color:#7ee787; background:#2ea04326; border:1px solid #2ea04366; }
      .badge.Medium { color:#e3b341; background:#bb800926; border:1px solid #bb800966; }
      .badge.Weak   { color:#ff7b72; background:#da363326; border:1px solid #da363366; }
      .tl-note { font:12px ui-monospace,monospace; color:#768390; }
      .stButton>button { width:100%; background:#238636; color:#fff; border:0;
        border-radius:8px; padding:.55rem; font-weight:600; }
      .stButton>button:hover { background:#2ea043; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<span class="tl-tag">PUBLIC DEMO · READ-ONLY · NO DATA STORED</span>',
            unsafe_allow_html=True)
st.title("🔐 Secure Password Generator")
st.caption(
    "Live demo of a CLI security tool: CSPRNG generation, entropy & crack-time "
    "estimation, and privacy-preserving breach checking via k-anonymity."
)

# --- Session state for soft rate limiting ----------------------------------
if "gen_count" not in st.session_state:
    st.session_state.gen_count = 0
if "hibp_count" not in st.session_state:
    st.session_state.hibp_count = 0
if "last_pw" not in st.session_state:
    st.session_state.last_pw = None

# --- Controls --------------------------------------------------------------
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    nr_letters = c1.slider("Letters", 0, MAX_PER_POOL, 12)
    nr_symbols = c2.slider("Symbols", 0, MAX_PER_POOL, 3)
    nr_numbers = c3.slider("Numbers", 0, MAX_PER_POOL, 3)

    o1, o2 = st.columns(2)
    exclude_ambiguous = o1.toggle("Exclude ambiguous (0 O l 1 I)", value=False)
    show_pw = o2.toggle("Show password", value=True)

    breach_check = st.toggle(
        "Live HaveIBeenPwned breach check (off by default)",
        value=False,
        help="Off by default so this public demo doesn't proxy traffic to HIBP. "
             "When on, only the first 5 chars of the SHA-1 hash leave the browser "
             "(k-anonymity). Limited per session.",
    )

    total = nr_letters + nr_symbols + nr_numbers
    generate = st.button("Generate password", type="primary")

# --- Generation ------------------------------------------------------------
if generate:
    if total == 0:
        st.error("Pick at least one character type.")
    elif total < int(os.environ["MIN_PASSWORD_LENGTH"]):
        st.error(f"Minimum length is {os.environ['MIN_PASSWORD_LENGTH']} characters.")
    elif total > MAX_TOTAL_LENGTH:
        st.error(f"Demo cap is {MAX_TOTAL_LENGTH} characters total.")
    elif st.session_state.gen_count >= SESSION_GEN_LIMIT:
        st.warning("Session generation limit reached. Reload the page to continue.")
    else:
        st.session_state.gen_count += 1
        # --- real logic, unchanged ---
        password = generate_password(nr_letters, nr_symbols, nr_numbers, exclude_ambiguous)
        strength = get_strength(nr_letters, nr_symbols, nr_numbers)
        entropy = calculate_entropy(total, nr_letters, nr_symbols, nr_numbers, exclude_ambiguous)
        crack_time = time_to_crack(entropy)
        st.session_state.last_pw = {
            "password": password, "strength": strength,
            "entropy": entropy, "crack_time": crack_time,
            "breach": None,
        }

        # Opt-in breach check, session-limited
        if breach_check:
            if st.session_state.hibp_count >= SESSION_HIBP_LIMIT:
                st.session_state.last_pw["breach"] = "limit"
            else:
                st.session_state.hibp_count += 1
                with st.spinner("Checking HaveIBeenPwned (k-anonymity)…"):
                    st.session_state.last_pw["breach"] = check_hibp(password)

# --- Output ----------------------------------------------------------------
res = st.session_state.last_pw
if res:
    st.markdown("### Result")
    display = res["password"] if show_pw else "•" * len(res["password"])
    st.markdown(f'<div class="tl-pw">{display}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tl-note">Triple-click to select · nothing is stored server-side</div>',
                unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.markdown(
        f'<div class="tl-metric"><div class="k">Strength</div>'
        f'<div class="v"><span class="badge {res["strength"]}">{res["strength"]}</span></div></div>',
        unsafe_allow_html=True)
    m2.markdown(
        f'<div class="tl-metric"><div class="k">Entropy</div>'
        f'<div class="v">{res["entropy"]:.1f} bits</div></div>', unsafe_allow_html=True)
    m3.markdown(
        f'<div class="tl-metric"><div class="k">Est. crack time</div>'
        f'<div class="v">{res["crack_time"]}</div></div>', unsafe_allow_html=True)

    st.write("")
    b = res["breach"]
    if b is None and breach_check is False:
        pass
    elif b == "limit":
        st.warning("Breach-check limit for this session reached.")
    elif b is None:
        st.info("Could not reach HaveIBeenPwned — breach check skipped.")
    elif b == 0:
        st.success("Not found in any known breaches.")
    elif isinstance(b, int) and b > 0:
        st.error(f"⚠️ Appeared in {b:,} known data breaches — do not use.")

# --- Footer ----------------------------------------------------------------
st.divider()
st.markdown(
    '<div class="tl-note">'
    'How it works: cryptographically secure generation via Python\'s <code>secrets</code> '
    'module; entropy from the active character pool; breach checking uses HIBP\'s range API '
    'so the full password hash never leaves your browser. '
    'This demo is read-only and rate-limited.'
    '</div>',
    unsafe_allow_html=True,
)
