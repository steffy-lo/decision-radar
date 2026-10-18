# Decision Radar submission checklist

Updated 18 October 2026 for [draft PR #31](https://github.com/steffy-lo/decision-radar/pull/31). Checked items refer to the evidence stated here. Material checks do not close application-readiness tickets or establish a new end-to-end pass.

## Submission materials completed

- [x] Use the prescribed template in the [current Google Slides deck](https://docs.google.com/presentation/d/1po5L-kgbXIouKNFhlRipmtPI-acJCDOCjRGkZ1x8DA8/edit). It contains 14 slides, with **Future of Work & Enterprise Productivity** as the category/theme, GeminiMaxxing as the team name, and Mike Umali as team leader.
- [x] Include the reported 17 October staging results, Microsoft Work Trend Index statistic, public repository link and future-development roadmap in the working deck.
- [x] Replace the earlier 1:56 preview on the Links slide (slide 13) with the [final 3:25 English demo with captions](https://drive.google.com/file/d/18AG5b-67JpuyGSGHrtuknta6BowcyEUM/view?usp=sharing), as supplied in [Mike’s final-video comment](https://github.com/steffy-lo/decision-radar/pull/31#issuecomment-6243842082). Update the label and duration, and remove the pending-video wording.
- [x] Export the updated Google Slides directly to [the submission PDF](DecisionRadar_Proposal.pdf) on 18 October. Inspect all 14 rendered pages, confirm selectable text and link annotations, and verify that the old video URL is absent. The other 13 pages render identically to the pre-edit Google Slides export.
- [x] Open the updated Links slide in Google Slides, click the demo link and start playback. The player opens `DecisionRadar_Demo_v5_captions.mp4`, displays 3:25 and advances during playback. This was a signed-in browser check, not complete signed-out playback.
- [x] Link the current Slides, PDF and final video from [technical documentation](TECHNICAL_DOCUMENTATION.md). Label the retained [PPTX](DecisionRadar_Proposal.pptx) as a historical snapshot; it does not match the current prescribed-template deck.

## Remaining before PR merge

- [ ] Review the materials against the final deployed web/API/worker revisions after dependency merges. Reconcile claims, screenshots, citations and source references with dated UAT evidence. Configurable model defaults do not prove the deployed model version.
- [ ] Verify all submission links signed out, including the PDF download and complete final-video playback. Mike reports signed-out video access in his comment; the checks in this update used a signed-in browser.
- [ ] Complete required repository checks and human PR review. Keep PR #31 draft until its remaining gates are resolved.

## Remaining before project submission

- [ ] **KAN-12 / KAN-25 / KAN-26:** reconcile final deployment, secret-provisioning and release evidence. [Mike’s 17 October report](https://github.com/steffy-lo/decision-radar/pull/31#issuecomment-6235417096) records two fresh full staging runs through actual Google Docs export and worker recovery with no duplicates. Run 1 evidence is in [PR #27](https://github.com/steffy-lo/decision-radar/pull/27), `docs/DEPLOYED_REHEARSAL1_UAT_20261017.md`. Rerun the integrated path after relevant deployment or dependency changes.
- [ ] Confirm unchanged replay, failure/retry, pause/resume, Doc/TXT/direct-subfolder/saved-transcript paths and export recovery without duplicate results. Record FAIL, BLOCKED and NOT TESTED honestly. Exercise tables or substantive automatic Meet-to-alert behavior before claiming them in the final demo.
- [ ] **KAN-24:** finish keyboard navigation/focus, graph selection, responsive and contrast checks across setup, decisions, reviews and briefs. Slide/PDF review does not complete application accessibility UAT.
- [ ] Arrange and test judge access to a connected project, including the approved OAuth account, membership and role. Disclose the native Drive ACL boundary; KAN-11 remains deferred. The public homepage fixture does not prove connected live-service access.
- [ ] Review the complete video for agreement with actual capabilities, dates and limits. Preserve synthetic-data labels and identify any fixture fallback.
- [ ] Confirm the submission form’s category mapping and exact cutoff/timezone for the published 18 October deadline.
- [ ] Submit the finalized PDF, public repository, prototype and final video links; verify signed-out access and retain confirmation.

## Material-validation evidence

The current PDF was exported directly from the native Google Slides deck and rendered with Poppler. Every page was visually inspected; PDF text and source/repository/prototype/video annotations were checked. Only the Links slide changed in this update. The final PDF SHA-256 is `cd88efc0729d2e2da80d6b4f2b3a36bb9a1455973653850eddc847a3eaca6eb0`.

Google Slides browser inspection and initial video playback passed. Complete playback and all-assets signed-out verification remain open. No new application release UAT, accessibility audit, load test or native PowerPoint check was performed. Historical prototype screenshots remain dated 10 October; the deck distinguishes them from the reported 17 October staging runs.

The retained PPTX’s earlier Artifact Tool and LibreOffice validation applies only to that historical file. It does not validate the current Google Slides deck or PDF.

## Evidence and sources

- [Final video and scope](https://github.com/steffy-lo/decision-radar/pull/31#issuecomment-6243842082): 3:25, folder connection, quote-backed decision confirmation, technology overview and worker recovery.
- [17 October staging report](https://github.com/steffy-lo/decision-radar/pull/31#issuecomment-6235417096): two fresh runs through actual Docs export; worker recovery with zero duplicates; about 9 seconds to a verified fact and 16 seconds for assessment, each a single observation.
- [Microsoft, Will AI Fix Work? (2023)](https://www.microsoft.com/en-us/worklab/work-trend-index/will-ai-fix-work/): the working deck’s 62% information-search statistic, based on 31,000 respondents across 31 markets.
- [Quality evaluation](../docs/KAN23_QUALITY_EVALUATION.md), [older rehearsal record](../docs/KAN26_DEMO_REHEARSAL.md) and [deployment UAT](../docs/CLOUD_RUN_DEPLOYMENT_UAT_20261009.md): dated synthetic-data results and environment/retry limits.
- [Submission-form/template review](https://github.com/steffy-lo/decision-radar/pull/31#issuecomment-6235594799), [official requirements](https://aibuildercup.com/themes.html) and [published timeline](https://aibuildercup.com/): prescribed template, public repository, 3–4 minute video, and remaining form/cutoff confirmation.
