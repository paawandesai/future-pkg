# future-pkg: knowledge-graph coach dashboard

> **Demo — synthetic data only.** The member in this project is fictional.

Coach decision support for personal-training coaches. It drafts workouts from a
knowledge graph of exercises, anatomy and a member's context, explains each
choice with a provenance trace, and waits for the coach to confirm the plan.
It does not produce medical advice and does not decide that any workout is safe.

Work in progress. Sections below are filled in as each part lands.

## Knowledge sources and licences

See `docs/alignment.md` and `NOTICE`. SNOMED CT is used by reference only: the repository
stores SNOMED identifiers and our own labels, never SNOMED descriptions.

Production use of SNOMED CT requires Future to hold a SNOMED International Affiliate license
(free in the US via the NLM UMLS license, with registration and usage reporting; fee-bearing in
non-Member countries).

This material references SNOMED Clinical Terms® (SNOMED CT®), which is used by permission of
SNOMED International. All rights reserved. SNOMED CT® was originally created by the College of
American Pathologists. "SNOMED" and "SNOMED CT" are registered trademarks of SNOMED International.

## Known constraints

- Hosted on GitLab rather than GitHub.
- `data/` is fetched at build time (`make data`) from a pinned commit of the
  assessment repo and is never committed, because that repo carries no license.
- The SNOMED live check depends on NCI EVS being reachable. It runs when alignments change and on
  a schedule, not on every push.
