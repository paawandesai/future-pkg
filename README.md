# future-pkg: knowledge-graph coach dashboard

> **Demo — synthetic data only.** The member in this project is fictional.

Coach decision support for personal-training coaches. It drafts workouts from a
knowledge graph of exercises, anatomy and a member's context, explains each
choice with a provenance trace, and waits for the coach to confirm the plan.
It does not produce medical advice and does not decide that any workout is safe.

Work in progress. Sections below are filled in as each part lands.

## Known constraints

- Hosted on GitLab rather than GitHub.
- `data/` is fetched at build time (`make data`) from a pinned commit of the
  assessment repo and is never committed, because that repo carries no license.
