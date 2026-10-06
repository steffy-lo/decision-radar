# KAN-24 impact graph resize check

6 October 2026. The graph was tested in the running Next.js app on port 3013 against the merged FastAPI service on port 8012, with Firebase Auth and Firestore emulators. The project contained an alert from a saved fact created during an earlier real Drive and Vertex run, plus two test dependencies in the emulator.

The existing graph fitted all four nodes when loaded at desktop or phone width. Resizing the open desktop page to a 390 px viewport left the nodes offscreen until Fit View was clicked. The canvas now remounts the read-only graph after its size changes so React Flow recalculates the fit. The selected node stays in component state.

After the change, I opened the alert at desktop width, resized to 390 px, and saw the trigger and downstream path centered without clicking Fit View. I focused the final downstream node and pressed Enter. The selected detail showed the four-step ordered path and said that node had no direct contradiction evidence. The viewport was restored afterward.

This checks the authenticated browser, API, and emulator data path for this layout fix. It does not include a fresh Drive refresh, a new Vertex extraction, or deployed Cloud Run. KAN-24 remains broader than this one fix.
