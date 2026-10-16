# Phase C — qualification gate for general ijtihad operators

**Status: implementation of a technical admission gate; no scientific promotion.**

Starting point: Phase B `ca7259a251743395bc8f2957509e7147446100dd`. This branch adds NO historical or hypothetical fiqh conclusions and changes NO `engine2/` files. The 13 imported Ansari legacy rules remain grade C, pending, hypothetical.

## Two distinct gates

1. **Neutral operator contract** (`operator_catalog.json`): shared software mechanisms for evidence identity, semantic scope, contradiction detection, etc. Their declared output is an audit result, not an Ansari-specific ruling. They must not be executed as a juristic authority without a qualifying `method_rule` for the selected scholar and methodology.
2. **Scholar-specific scientific qualification** (`architecture/migrations/004_phase_c_qualification.sql`): a rule's historical promotion requires a reviewed methodology profile, scientific A/B, six supported components (scope, activation, defeaters, exceptions, conflict policy, principle), each with a source passage marked `matched` and an accepted per-component textual review. Two distinct reviewer decisions are required. Grade A additionally needs an explicit principle backing; grade B requires two independently declared groups with distinct principle passages. Open/contested objections block promotion.

**Important limitations:** These are structural and provenance controls. Two human review labels in SQL do NOT prove two independent human experts existed; a SHA does NOT hide test answers; `capture_status=matched` does NOT prove a historical quotation was rightly interpreted; independence groups are an *assertion awaiting external verification*. Therefore passing this gate alone does **not** certify a historical rule or move the project to ijtihad level 4. The pilot has zero scientifically qualified historical rules at creation.

## Original weakness corrected

The previous `002_cross_scholar_integrity.sql` gate checked the presence of six `rule_backings`, but **all six could point to the same unreviewed passage**. A synthetic fixture in `001_smoke.sql` deliberately demonstrated that this was technically allowed. This Phase C migration adds a stricter promotion guard; earlier tests remain historical evidence of the old relational contract and are run **before** the stricter migration. They are not an oracle for scholarly qualification.

## Repeatable execution

Requires PostgreSQL 16 and psycopg 3. Schema/tests run in the following order:

```bash
psql -v ON_ERROR_STOP=1 -f architecture/migrations/001_issue_centric_multischolar.sql
psql -v ON_ERROR_STOP=1 -f architecture/migrations/002_cross_scholar_integrity.sql
psql -v ON_ERROR_STOP=1 -f architecture/migrations/003_phase_b_evidence_relations.sql
psql -v ON_ERROR_STOP=1 -f architecture/tests/001_smoke.sql
python -m phase_b.pilot
psql -v ON_ERROR_STOP=1 -f architecture/migrations/004_phase_c_qualification.sql
psql -v ON_ERROR_STOP=1 -f architecture/tests/004_qualification_smoke.sql
python -m phase_c.qualification_report --assert-baseline
```

The SQL fixture is wholly synthetic and uses `BEGIN...ROLLBACK`. In particular, it attempts and rejects promotion with zero sources, six unreviewed sources, one approval, one grade-B witness and an open objection, then admits structurally qualified synthetic A/B examples **inside the rollback-only transaction**. No real pilot scientific grade is changed.

## Independent scholarship task before any real rule admission

For each proposed general operator, a separate scientific packet must state:
- full Ansari quote and edition, work, DB record/printed page and context, identity and authenticity;
- **which reasoning behavior** is claimed, and any competing reading;
- why the claim follows from the quote (semantic license), not from an extractor tag;
- subject/issue scope, activation conditions, defeaters, exceptions, conflict priority and their own textual backing;
- A explicit statement versus B strong inference with two actually independent pieces of evidence, not merely two database rows;
- adverse evidence, changes of view, relation to Farāʾid and Makāsib, and a scope-limited search statement;
- independent qualified human sign-off and grade; only then a new versioned methodology profile and frozen ruleset.

Suggested **research candidates, not certified rules**: same-subject checks before labeling taʿāruḍ; valid qarīna before jamʿ; naṣṣ/ẓāhir scope; issue of `al-jamʿ mahmā amkan`; separation of evidence assessment (ṣudūr, dalāla, jiha, ḥujjiyya); and justified stop. These are *questions for research*, not logic hardcoded from the Udhrah outcomes.

## Next milestone (not delivered by this PR)

Deliver an independent text-grounded dossier for the first general operator using original Farāʾid passages, an **outside-the-development-data** test set with a hidden adjudication key, and a separate engine adapter under review. Do not reuse the Udhrah case as the sole source and judge of its own rules. Keep PR #1, #2 and #3 unmerged and track their branch dependencies until all checks pass.

## CI and non-goals

Workflow `Feqh-Muse Phase C qualification` validates schema+pilots, the negative qualification controls, read-only status report, and regression tests 6/8 and mutations. This is *not* a release of a general fiqh inference engine. No model inference is used as a substitute for source-specific human review.
