---
trigger_when: GEX page rework, dealer-gamma analytics, or "how brittle is the tape today" hedge-timing context
planted_during: v3.5 discuss-phase 15 (2026-06-04)
area: gex / dealer-positioning
---

# SEED-001: Short-end gamma concentration (0DTE / front-expiry GEX)

## The Idea

On the GEX page (page 3 in the v3.5 reorg), break out **how much dealer gamma is concentrated in the short end** — same-day (0DTE) and front-expiry — relative to total net GEX. Reads as "how aggressively is the market positioned on the front end right now." A DTE bucket / front-expiry share on `strike_gex` and `gamma_profile`.

## When to Surface

- A future milestone reworks the GEX page or adds dealer-gamma analytics
- Hedge-timing / "is the tape brittle today" context is being built out
- The parked "large OI blocks expiring soon" item is revisited (this supersedes/merges it)

## Why This Matters

0DTE went from a niche to ~40–50% of SPX options volume in ~2 years — a real market-structure shift. Short-dated gamma concentration drives intraday pinning, vol suppression/amplification, and front-of-curve term behavior (VIX9D is increasingly a 0DTE artifact). It's genuine dealer-positioning context for hedge timing.

**NOT for the lead VRP page.** The discretionary income PMs write 30–45 DTE; 0DTE doesn't change *where they write*. This is GEX/dealer-gamma context only. The Yield Shares product writes weeklies but is automated — no discretionary dashboard user there either.

## Constraints / Notes

- **Data already exists** — the GEX module pulls the full chain per ticker with no DTE filter (`CLAUDE.md` GEX section). This is a presentation breakout, not a new data source. Cheap.
- **Parameter-free split preferred** — 0DTE (expiry == today) and front-expiry share are clean/defensible. A "near-dated ≤N days" cutoff is a *chosen parameter* — this project has scars from hand-tuned cutoffs (retired wall-cluster, $200M regime floor). Pick deliberately or stay parameter-free.
- **Merges the parked item** "Large OI blocks expiring soon" (STATE.md Deferred / REQUIREMENTS Future) — same idea, needs the same parameter-free design.

---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/gamma-omm/ROADMAP|ROADMAP]] · [[_planning/gamma-omm/STATE|STATE]] · [[gamma-omm/gamma-omm|Hub]]
<!-- LINKS:END -->
