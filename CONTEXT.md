# CONTEXT.md - Sprint 3: Resolving the Live Prediction Tie Bug

## Mission Objective
Fix a critical probability calculation bug in `tools/predict_games.py`. The live engine is currently using `1 - skellam.cdf(0, ...)`, which fails to correctly account for ties (which are impossible in MLB) and distributes the win probability inaccurately.

## Rules of Engagement
* **Target File:** `tools/predict_games.py` only.
* **Read-Before-Write:** Read the file completely before suggesting any code modifications.
* **The Fix:** Replace the current probability calculation with the "Skellam Correction" documented in our research notes. Specifically:
    1. Calculate the raw home win probability using `skellam.sf(0, y_pred[:, 0], y_pred[:, 1])`.
    2. Calculate the tie probability using `skellam.pmf(0, y_pred[:, 0], y_pred[:, 1])`.
    3. Calculate the final `probs` by dividing the home win probability by `(1 - tie_probability)`.
* **Output:** Provide the exact, refactored code block for step 4 ("Generate Probabilities") inside `tools/predict_games.py`.
