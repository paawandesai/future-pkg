# UI design

The UI was designed in Claude Design. Paawan approved the design on 2026-10-15 (checkpoint D).
No design system was used.

The canvas (artboards: Login, Main, GeneratorStates, Copilot) is a private Claude Design artifact,
so this link opens only for its owner: https://claude.ai/artifact/LFAMMfCguDPbdCxpcrBaL9. The
deployed demo and `web/` are the reviewable result.

The React app (`web/`) rebuilds those artboards as components. The canvas HTML is a reference
only and was not copied in. Its colors and type became CSS variables in `web/src/styles.css`
(IBM Plex Sans and Mono).

Every string from the API renders as text. ESLint rejects `dangerouslySetInnerHTML` and
`innerHTML`.

The React build differs from the canvas in four places, each on purpose:
- "Why this plan" says the trace is recorded by the filter and scorer. The canvas said "wording
  drafted with AI". The build renders the trace from a template, so the model writes none of it.
- The churn panel shows our score as points out of 11, with each feature's points.
- The minutes field is optional. When it's empty, the minutes in the request apply, then the
  member's preferred session length.
- The member-message notice uses neutral wording ("If a clinician has cleared the member").
