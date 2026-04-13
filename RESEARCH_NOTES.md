# Research Notes: The ReAct Pattern in Autonomous Agents

## Case Study: Self-Correction in the MLB Betting Agent
**Date:** April 12, 2026
**Subject:** Observational analysis of a multi-turn ReAct (Reasoning + Acting) loop.

### 1. The Observation
During a query regarding "Pitchers with high ERA-SIERA differentials and their K-BB%," the agent provided two distinct text outputs. 
- **Output A:** A list of pitchers meeting the ERA/SIERA criteria.
- **Output B:** The same list, but enriched with the requested K-BB% metrics.

### 2. The Mechanics of the ReAct Loop
The agent follows the **ReAct (Reason + Act)** framework. This is implemented in `agent.py` via a `while response.function_calls` loop. The cycle functions as follows:

1.  **Reasoning:** The LLM analyzes the user prompt and determines what data is missing.
2.  **Acting:** The LLM generates a tool call (SQL query).
3.  **Observation:** The Python script executes the SQL and feeds the results back to the LLM.
4.  **Refinement:** The LLM compares the "Observation" with the original "Goal."

### 3. Deep Dive: The "Self-Correction" Phenomenon
In this specific instance, the agent demonstrated **Autonomous Recovery**. 

*   **The Initial Failure:** In the first "Action" phase, the agent generated a SQL query that selected `name`, `era`, and `siera`, but omitted `k_minus_bb_percent`. 
*   **The Mid-Loop Realization:** Upon receiving the results of Query 1 (the Observation), the agent's internal reasoning recognized a **Gap in Fulfillment**. It realized it had the list of pitchers but could not yet provide the K-BB% statistics requested by the user.
*   **The Second Action:** Instead of terminating the loop or asking the user for help, the agent immediately generated a second Tool Call to fetch the missing `k_minus_bb_percent` for that specific list of players.
*   **The Final Response:** Only once the "Observation" matched the "Goal" (having all three metrics) did the agent exit the tool-calling loop and provide the final synthesis.

### 4. Significance for Research
This behavior highlights the superiority of **Stateful Agentic Loops** over simple "one-shot" prompting. 

- **Reliability:** In a one-shot system, the missing K-BB% would simply be a failed requirement. In a ReAct system, the agent has the "agency" to recognize its own mistake and fix it dynamically.
- **Explainability:** The "Double Output" seen in the terminal is a window into the agent's "Chain of Thought." It allows the developer to see exactly where the agent pivoted from a partial answer to a complete one.

### 5. Technical Implementation Details
The loop is sustained by the following Python logic:
```python
while response.function_calls:
    # 1. Capture the 'Action' (Function Call)
    # 2. Execute the 'Observation' (SQL Execution)
    # 3. Feed back to the LLM
    response = chat.send_message(types.Part.from_function_response(...))
    # Loop repeats if the LLM decides it needs more data
```
This ensures the agent remains in a "Thinking" state until it explicitly decides it has sufficient information to respond to the user.

---

## Machine Learning Pipeline: Feature Engineering & Model Selection

### 1. The Training Dataset
A specialized repository, `historical_training_data`, was constructed to facilitate supervised learning. 
- **Sample Size:** 8,551 games (comprising the full 2023, 2024, and 2025 MLB regular seasons).
- **Ingestion Methodology:** Data was fetched sequentially via the MLB StatsAPI using a monthly chunking strategy to ensure 100% uptime and bypass API timeout restrictions.

### 2. Feature Architecture (Independent Variables)
The dataset utilizes a "Mirrored Feature Set," where every training column has a corresponding live equivalent in the `betting_markets` table. Key features include:
- **Pitching Stability:** Rolling SIERA and K-BB% for both starting pitchers and relief corps.
- **Offensive Variance:** Team-level ISO and wOBA, filtered by pitcher-handedness (LHP/RHP platoon splits).
- **Environmental Anchors:** Stadium-specific park factors, real-time temperature, and wind velocity.

### 3. Avoiding Temporal Data Leakage
A critical component of this research was the implementation of a **Rolling cumulative feature store**. By utilizing the vectorized Pandas `.shift(1)` operation during dataset generation, the system ensures that every game’s features represent the "Current State" of player skill *prior* to the first pitch. This eliminates "Look-Ahead Bias," ensuring that end-of-season results do not pollute early-season predictions.

### 4. Future Research: Model Comparison
The next phase of research will involve a head-to-head performance comparison between two distinct architectural approaches to calculate the Win Probability ($p$):

1.  **Gradient Boosted Decision Trees (XGBoost):**
    - **Hypothesis:** XGBoost will excel at handling the non-linear relationships between environmental variables (Wind/Temp) and proprietary skill metrics (SIERA).
    - **Optimization:** Hyperparameter tuning using Bayesian Optimization.

2.  **Deep Learning (Neural Network):**
    - **Hypothesis:** A multi-layer perceptron (MLP) architecture may identify subtle, latent interactions between platoon splits and bullpen fatigue that traditional tree-based models might overlook.
    - **Architecture:** Dense layers with Dropout for regularization and a Softmax output for binary classification (Win/Loss).

### 5. Evaluation Framework
Both models will be evaluated using **Log-Loss** (to measure the accuracy of the probability estimates) and **Kelly ROI**. The ultimate goal is to determine which architecture provides the most accurate $p$ value for the Kelly Criterion tool, thereby maximizing long-term bankroll growth.
