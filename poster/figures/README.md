# PSP305 design figures — draft images

AI-assisted visual drafts created 2026-11-24, based on Model 0 specification and verification plan at development revision `1d51704`. Student review required before assessment use; record AI assistance in Appendix B.

- `01_mas_architecture.png`: conceptual architecture. Correction needed: coordinator and travel handling already exist in Model 0; the dashed legend must not imply they are deferred. Policy experiments are planned, not completed. Routing does not directly assign a resource: travel precedes station queue entry.
- `02_agent_interaction.png`: conceptual interaction sequence, not actual method calls or trace. Coordinator orders domain phases; Station owns selection, completion and release. Model 0 patients follow B0.
- `03_patient_lifecycle.png`: conceptual successful patient lifecycle; transitions after service require resource release and committed state.
- `04_centre_layout.png`: synthetic illustrative spatial layout, not a measured floor plan or calibrated travel network. Model 0 travel times are A–B 1, B–C 1, A–C 2 minutes; entrance to first station 0.
- `05_queue_policy_comparison.png`: illustrative service orders for four waiting patients, expected service durations 5, 2, 8, 3 min. Read displayed service order left to right, regardless of server icon placement. SPT is a candidate, not selected or evaluated. Patient labels are illustrative, not package identifiers.
- `06_verification_timeline.png`: T01 theoretical expectation (A 0–4, travel 4–5, B 5–8; wait 0), not a new execution result.
- `01_mas_architecture_earlier_draft.png`: earlier conceptual draft, not preferred for final poster.

References: `../../docs/MODEL_SPEC.md`, `../../docs/VERIFICATION_PLAN.md`, `../../docs/LITERATURE_LIBRARY.md`, `../../PROJECT_PROGRESS.md`.

These raster drafts are not editable SVGs. No Gate 1 completion, new research results, or real hospital layout is claimed.
