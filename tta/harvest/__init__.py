"""Getting an account's catalogue, in three tiers.

1. `ytdlp`  — flat enumeration. Fast, keyless, structured. The default.
2. `camofox` — stealth browser, for when tier 1 is blocked.
3. `chrome_handoff` — the user's own logged-in browser, on explicit permission.

Every tier produces the same record shape, so everything downstream is
indifferent to which one ran.
"""
