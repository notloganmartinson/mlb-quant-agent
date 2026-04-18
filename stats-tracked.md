# MLB Agent: Tracked Statistics & Features

This document serves as the canonical reference for all data points tracked in the `mlb_betting.db` and utilized by the machine learning models.

## 1. Advanced Pitching Metrics (Performance Baseline)
*   **SIERA (Skill-Interactive ERA):** Measures true talent by accounting for K rate, BB rate, and batted ball profile.
*   **K-BB% (Strikeout minus Walk %):** Indicator of pitcher dominance and zone control.
*   **Stuff+ (Pitch-Level Model):** Score based on velocity, vertical/horizontal movement, and release point (VAA).
*   **VAA (Vertical Approach Angle):** The angle the ball enters the zone; determines "rising" or "flat" fastball perception.
*   **Break Magnitude:** Total physical movement of a pitch in inches.
*   **Rolling Stuff+:** Point-in-time average leading up to a game to avoid look-ahead bias.

## 2. Hitting & Lineup Metrics (The Opposition)
*   **Lineup ISO (Isolated Power):** Measures extra-base hitting potential (Extra Bases / AB).
*   **Lineup wOBA (weighted On-Base Average):** Comprehensive run-scoring value weight for all reach-base events.
*   **Lineup K% (Strikeout Propensity):** The percentage of time the starting 9 hitters strike out.
*   **Lineup PA (Experience):** Plate appearances accumulated to weight stat reliability.
*   **Handedness Splits:** All hitting stats are filtered by the L/R handedness of the opposing starting pitcher.

## 3. Market & Betting Data (Financial Evaluation)
*   **Closing Moneyline:** Final market price for the win/loss outcome.
*   **Closing Total:** Final market price for total runs (Over/Under).
*   **K-Prop Line:** The sportsbook's set line for pitcher strikeouts (e.g., 5.5).
*   **K-Prop Odds:** The price/juice associated with the strikeout line (e.g., -115).
*   **Implied Probability:** The percentage chance the market assigns to an outcome (1 / Decimal Odds).

## 4. Environmental & Contextual Edges (The "Alpha")
*   **Umpire K% (Home Plate):** Historical strikeout tendency of the assigned home plate umpire.
*   **Park K-Factor:** Venue-specific multiplier for strikeout frequency (derived from Home vs. Away K% ratios).
*   **Temperature:** Impact of air density on ball flight and pitch movement.
*   **Wind Speed & Direction:** Impact on run scoring and home run probability.

## 5. Model Targets (Labels)
*   **Home Team Win (0/1):** For win-probability classification.
*   **Total Runs:** For run-total regression.
*   **Actual Pitcher Strikeouts:** Discrete count for Poisson regression backtesting.
