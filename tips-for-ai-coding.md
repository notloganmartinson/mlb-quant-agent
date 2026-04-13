# Tips for AI-Assisted Coding: The "MLB-Agent" Protocol

These tips are derived from the successful refactor and development of the MLB Quant Betting Agent. They focus on maximizing AI precision while minimizing context bloat and logic errors.

## 1. try and take on parts of project one at a time to avoid confusing model. do sanity check often.

## 1. Context & Memory Management
*   **Shatter the Monoliths:** As soon as a script handles more than two distinct domains (e.g., Stats + Weather + Odds), break it into atomic modules. Large files cause "Context Saturation," leading to formatting errors and "Internal Monologue Leakage" (where the AI outputs its raw thoughts).
*   **Use an AST Repo Map:** Don't just give the AI a README. Use a script to generate a `GEMINI.md` containing class and function skeletons (AST Map). This provides 100% structural awareness with 5% of the token cost.
*   **Session-Specific Grounding (`CONTEXT.md`):** For every new session or sprint, create a lean `CONTEXT.md`. This file should act as the "Mission Control" for the current task. It provides the AI with its high-level goal, specific rules of engagement (e.g., "Shatter these 3 files"), and the immediate constraints of the session. Keeping this file focused prevents the AI from getting bogged down in the irrelevant history of the project while it's trying to execute a specific sprint.
*   **Clear the "Working Memory":** If the AI starts leaking `[Thought: true]` tags or raw JSON, it's a sign of context overload. Refactor immediately to reduce the per-turn token requirements.

## 2. Preventing Hallucinations (Grounding)
*   **Schema Isolation:** Never hardcode SQL strings in Python logic. Keep a `schema.sql` file. This allows the AI to read the "Source of Truth" directly, ensuring it generates 100% accurate JOINs and queries.
*   **Read-Before-Write Protocol:** Instruct the AI to never assume logic exists. Force it to request a file read before it attempts a modification.
*   **Canonical Mapping:** Use a "Translator" table (like `team_mappings`) for multi-provider data. AI struggles with fuzzy string matching; it excels with strict Integer ID joins.

## 3. The "Fail-Fast" Stability Layer
*   **Mathematical Guardrails:** Wrap all pure functions in strict `assert` statements. If a formula expects Plate Appearances > 0, assert it. It's better for the script to crash immediately than to save "Silent Failures" (NaNs or zeros) to your database.
*   **Snapshot Verification:** When refactoring a data pipeline, don't just check if it runs. Write a script to compare the new output against the old output. Aim for **100% identical data** before deleting the old code.
*   **Pure Function TDD:** Keep your math in a dedicated `stats_calculator.py` and maintain a unit test suite. This ensures that no "just-in-case" AI edit accidentally breaks your underlying regression formulas.

## 4. Architectural Decoupling
*   **Dependency Injection:** Never hardcode paths like `data/my_db.db` inside a function. Pass the path as an argument or use an environment variable. This allows the AI to run tests against a "Sandbox" database without risking your production data.
*   **Class-Based Tools:** Wrap AI tools in a class (e.g., `MLBAgent`). This makes the state (like the DB connection) explicit and prevents the AI from getting lost in global variable scope.

## 5. The "Professional Trace"
*   **Document the Pitfalls:** Keep a `PITFALLS.md` file. Every time you hit a wall (like Cloudflare blocks or Data Leakage), document it. This serves as "Long-Term Memory" for both you and the AI in future sessions.
*   **Explain the "Why":** When asking the AI to refactor, explain the architectural goal (e.g., "Script Atomicity"). The AI performs better when it understands the **design pattern** it is expected to follow.
