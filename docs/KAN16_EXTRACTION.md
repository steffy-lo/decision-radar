# KAN-16 extraction slice

`services/radar/pipeline/gemini.py` sends one ready source snapshot to Vertex AI Gemini and requests structured decision and fact candidates. It uses the Google Gen AI SDK with Application Default Credentials and requires a real Google Cloud project ID. The model and location are constructor options. No key is stored in the repo.

`Extractor.extract(source, known_entities, native_url)` is the integration point for KAN-4. `known_entities` maps names found in the document, such as `vendor`, to trusted project IDs, such as `vendor_acme`. `native_url` must come from Drive metadata. The source snapshot and link must be saved before extraction begins.

Every quote must appear exactly once in the saved snapshot. The validator records its offsets and a span ID tied to that snapshot version. Missing or repeated quotes, invalid typed values, and malformed model output reject the whole extraction. Tentative wording, incomplete context, unresolved entity names, and dates or amounts absent from their quotes remain uncertain. An assumption with a date or amount absent from its quote also marks its decision uncertain. Explicit negations stay separate. Only `result.alert_eligible_facts` can enter the deterministic comparison in KAN-17.

The synthetic fixture and a fake model response cover this path in `tests/test_extraction.py`. A live Gemini request and Drive handoff still need project credentials and KAN-4's ingested source metadata.
