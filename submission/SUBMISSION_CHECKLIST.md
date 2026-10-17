# Decision Radar submission checklist

Updated 17 October 2026 for [draft PR #31](https://github.com/steffy-lo/decision-radar/pull/31). Checked items refer to the evidence stated here. They do not close application-readiness tickets or establish a new end-to-end pass.

## Submission materials completed

- [x] Correct the deck's technical flow: confirm the initial monitored decision before extracting facts; Gemini extraction runs through the API; Cloud Tasks queues refresh and deterministic assessment in the worker.
- [x] Correct the architecture arrow to show API-to-Vertex extraction and remove the worker extraction label.
- [x] Qualify the timing and rehearsal evidence: 25.2 seconds was one worker execution, about 30 seconds to visible completion. Older core rehearsals used retries/mixed environments; final rehearsals through export remain outstanding.
- [x] Describe table mapping, generated Meet intake and brief export as implemented with dated UAT limits. Keep native per-viewer Drive ACLs deferred under KAN-11.
- [x] State manual Drive refresh, the root/direct-subfolder boundary and 100-file cap, test-user OAuth and project-role access. Identify benefits as intended outcomes; remove unmeasured cost and exactly-once claims.
- [x] Verify problem statistics against primary sources, correct their populations/wording, and add source hyperlinks and speaker notes. Replace unsupported competitor scores with qualified category descriptions.
- [x] Replace the prototype placeholders on slides 1 and 14 with working hyperlinks. The public homepage returned HTTP 200 on 17 October. This did not test connected-project sign-in or judge access.
- [x] Use the exact **Future of Work & Enterprise Productivity** theme and English copy in the deck and technical documentation.
- [x] Preserve the existing 14-slide design and dimensions, correct heading wrapping, and inspect the rendered slides against the original.
- [x] Export the corrected [editable deck](DecisionRadar_Proposal.pptx) to a [14-page PDF](DecisionRadar_Proposal.pdf), inspect every page and check selectable text plus prototype/source link annotations. The PDF remains a draft because the video is pending.
- [x] Check sequential technical-document headings, relative links, balanced code fences and whitespace. Link the PDF and this checklist from [technical documentation](TECHNICAL_DOCUMENTATION.md).

## Remaining before PR merge

- [ ] Review the materials against the final deployed web/API/worker revisions after dependency merges. Reconcile any differences and retain dated UAT limits. Model labels currently say Gemini on Vertex AI; source defaults are not presented as proof of a deployed model version.
- [ ] Record and publish the three-minute English video. Replace the explicit pending message on slide 14 and add its public link to the technical documentation.
- [ ] Re-export and inspect the final PPTX/PDF after inserting the video URL; verify all final links in a signed-out browser. The earlier visual check does not cover future edits.
- [ ] Complete required repository checks and human PR review. Keep PR #31 draft until its remaining gates are resolved.

## Remaining before project submission

- [ ] **KAN-12 / PR #27:** clean integrated deployment, per-project secret provisioning and transient worker recovery drill; record revisions, IAM/health results and persisted recovery evidence.
- [ ] **KAN-25 / KAN-26:** two fresh end-to-end runs against real services, from connection and fresh source evidence through confirmation, extraction, assessment, citations, graph, human review, brief and actual Google Docs export. Use fresh reviewable alerts rather than clearing history or reopening an old result.
- [ ] Exercise unchanged replay, failure/retry, pause/resume, Doc/TXT/direct-subfolder/saved-transcript paths and export recovery without duplicate results. Record BLOCKED and NOT TESTED cases. Include tables or substantive automatic Meet-to-alert behavior if those are demonstrated or claimed in the final video.
- [ ] **KAN-24:** finish the full application keyboard, responsive, contrast and narrative checks. The slide/PDF review does not complete application accessibility UAT.
- [ ] Arrange and test judge access to a connected project, including the approved OAuth account, membership and role. Disclose the native Drive ACL boundary. The public fixture is not proof of live-service access.
- [ ] Verify final PDF download, public video access and complete playback signed out. Screens and narration must agree with actual capabilities, dates and limits.
- [ ] Inspect the submission form's theme choices and confirm the exact cutoff/timezone for the published 18 October deadline. Resolve any category mismatch with the organisers.
- [ ] Submit the final prototype/PDF/video links and required form fields, then retain confirmation.

## Material-validation evidence

The PPTX was imported, edited and rendered with Artifact Tool. Package integrity, geometry, 14-slide count, reference-font declarations and re-import checks passed. The PDF was exported with bundled LibreOffice, rendered with Poppler, and inspected page by page. It retains selectable text and clickable prototype/source references. Native PowerPoint was not used, and no new application UAT or load test was performed for these material edits. The historical screenshots remain dated evidence; the graph screenshot is an excerpt rather than a new full-path recording.

The staging API configuration was read without changing it: revision `decision-radar-api-staging-00014-42c`; no explicit `VERTEX_MODEL` environment override appeared. This does not independently identify the model used by that deployed image. The deck therefore avoids asserting a runtime model version.

## Sources checked

- [McKinsey, Decision making in the age of urgency (2019)](https://www.mckinsey.com/capabilities/people-and-organization/our-insights/decision-making-in-the-age-of-urgency): 37% refers to surveyed respondents' average time, not a universal manager estimate. The survey had 1,259 participants, with 1,228 familiar with organisational decision-making.
- [MGI, The social economy (2012)](https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/the-social-economy): nearly 20% refers to interaction workers finding information or helpful colleagues. These are historical estimates, not a current adoption or impact measure.
- [PMI, Pulse of the Profession (2018), printed appendix p. 25](https://www.pmi.org/-/media/pmi/documents/public/pdf/learning/thought-leadership/pulse/pulse-of-the-profession-2018.pdf): respondents selected up to three primary failure causes, including changed priorities (39%) and inaccurate requirements gathering (35%).
- [Quality evaluation](../docs/KAN23_QUALITY_EVALUATION.md), [rehearsal record](../docs/KAN26_DEMO_REHEARSAL.md), and [deployment UAT](../docs/CLOUD_RUN_DEPLOYMENT_UAT_20261009.md): dated synthetic-data results and environment/retry limits.
- [Official requirements](https://aibuildercup.com/themes.html) and [published timeline](https://aibuildercup.com/): final theme/form/cutoff confirmation and actual submission remain open.
