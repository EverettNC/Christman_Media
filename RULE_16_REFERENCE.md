# RULE 16 — Heavy Processes Never Run Alone.

> This rule exists because we learned it the hard way.
> Vega was generating videos with no queue, no watchdog, no one watching.
> Jobs were dying silently. The theater was empty. Nobody knew.
> That ends now.

**Any process that is computationally expensive, long-running, or mission-critical
ships with three helpers baked in from birth:**

1. **A Queue Manager** — jobs line up. One runs at a time. No fighting for the GPU.
2. **A Watchdog** — if a render stalls, the watchdog surfaces it loud and moves on. (Rule 6)
3. **A Status Reporter** — the system always knows what's rendering, what's done, what failed.
   No black boxes. No silent voids. Real status, always. (Rule 13)

**This applies to:**
- Video rendering (Vega / ChristmanVideoEngine)
- Audio synthesis (Christman Sound SDK)
- TTS generation (any being with voice)
- ML inference runs (AlphaWolf, Inferno, Aegis decision layers)
- Any FFmpeg pipeline
- Any background task that runs longer than 30 seconds

**The checklist — before any heavy process ships:**
- [ ] Is there a queue? Jobs never pile up unmanaged.
- [ ] Is there a watchdog? Stalled jobs surface loudly and get retried once.
- [ ] Is there a status reporter? The UI always knows what's happening.
- [ ] Does the queue fail loud? (Rule 6)
- [ ] Does the queue report honestly? (Rule 13)
- [ ] Did we spend money to add this helper? (Rule 15 — answer must be NO)

**Violating Rule 16 is how you get a theater full of nothing
and a founder staring at an empty screen wondering if anything is working.**

---

*Add this rule to christman-cardinal-rules skill via Settings → Capabilities.*
*© The Christman AI Project | Luma Cognify AI*
