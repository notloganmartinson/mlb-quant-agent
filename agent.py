import os
import time
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from core.db_manager import MLBDbManager
from tools.value_finder import ValueFinder
from tools.lineup_analyzer import LineupAnalyzer
from ingest_orchestrator import run_daily_stats_ingestion, run_odds_ingestion

load_dotenv()

class MLBAgent:
    def __init__(self):
        """
        Initializes the MLB Quant Agent with Dependency Injection for the database.
        """
        self.db_manager = MLBDbManager()
        self.value_finder = ValueFinder()
        self.lineup_analyzer = LineupAnalyzer()
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model_id = 'gemini-2.5-flash'

    def execute_sql(self, query: str) -> str:
        """
        Executes a read-only SQL query against the mlb_data PostgreSQL database.
        This is the agent's primary way to view stats and betting odds.
        """
        print(f"\n[TOOL CALL] Executing SQL: {query}")
        try:
            # Security check to prevent LLM from deleting tables
            if not query.strip().upper().startswith("SELECT"):
                return "Error: You are only allowed to run SELECT queries."

            results = self.db_manager.query_agent_data(query)

            # Format the output cleanly so LLM can read it
            if results:
                return str(results)
            else:
                return "Query executed successfully, but returned no data."

        except Exception as e:
            return f"SQL Error: {str(e)}"

    def get_live_schema(self) -> str:
        """Pulls the exact table structures directly from PostgreSQL using the injected manager."""
        sql = """
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            ORDER BY table_name, ordinal_position;
        """
        try:
            columns = self.db_manager.query_agent_data(sql)
            schema_map = {}
            for row in columns:
                table = row['table_name']
                if table not in schema_map:
                    schema_map[table] = []
                schema_map[table].append(f"{row['column_name']} ({row['data_type']})")
            
            formatted_schemas = []
            for table, cols in schema_map.items():
                formatted_schemas.append(f"Table: {table}\nColumns: " + ", ".join(cols))
                
            return "\n\n".join(formatted_schemas)
        except Exception as e:
            return f"Error retrieving schema: {e}"

    def fetch_daily_value(self) -> str:
        """Fetches structured daily value edges for MLB betting."""
        print(f"\n[TOOL CALL] Executing: fetch_daily_value")
        try:
            result = self.value_finder.find_value_today()
            return json.dumps(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Error fetching daily value: {str(e)}"

    def fetch_lineup_analysis(self) -> str:
        """Fetches structured lineup analysis for today's games."""
        print(f"\n[TOOL CALL] Executing: fetch_lineup_analysis")
        try:
            result = self.lineup_analyzer.run_daily_analysis()
            return json.dumps(result)
        except Exception as e:
            return f"Error fetching lineup analysis: {str(e)}"

    def refresh_data(self) -> str:
        """Manually triggers a full data refresh (stats, odds, and model predictions) for today's slate."""
        print(f"\n[TOOL CALL] Executing: refresh_data")
        try:
            run_daily_stats_ingestion(2026)
            run_odds_ingestion()
            return "Data successfully refreshed. All stats, odds, and model predictions are now up to date for today's slate."
        except Exception as e:
            return f"Error refreshing data: {str(e)}"

    def _get_config(self):
        """Builds the agent configuration with tools and dynamic system instruction."""
        return types.GenerateContentConfig(
            tools=[self.execute_sql, self.fetch_daily_value, self.fetch_lineup_analysis, self.refresh_data],
            system_instruction=(
                "You are a ruthless, quantitative MLB betting analyst. "
                "You have access to a PostgreSQL database containing advanced sabermetrics (SIERA, ISO, K-BB%, Bullpen metrics, Platoon Splits, Live Betting Markets, and Weather data). "
                f"You must query the PostgreSQL database using this exact live schema:\n\n{self.get_live_schema()}\n\n"
                "If a user asks about the 'active slate', 'matchups', 'today', or 'tonight', you MUST filter the query by joining the stats table with the betting_markets table to ensure you only analyze players actively participating in upcoming games."
                "Always filter queries to pitchers with IP > 10."
                "Base all recommendations on cold, hard math. Never guess stats. "
                "When asked for betting advice or daily value, you MUST first call fetch_daily_value. You may also call fetch_lineup_analysis to check situational context. Synthesize the JSON responses into a conversational betting recommendation."
                "If the user asks to 'update', 'sync', or 'refresh' the data, call the refresh_data tool."
            )
        )

    def run(self):
        """Starts the ReAct loop for the agent."""
        print("MLB Quant Initialized (DB: PostgreSQL). Type '\\q' to quit.\n")
        
        # Init stateful chat session
        chat = self.client.chats.create(
            model=self.model_id,
            config=self._get_config()
        )
        
        while True:
            try:
                user_prompt = input("> ")
            except EOFError:
                break
                
            # Robust quit logic
            if user_prompt.lower() in ['exit', 'quit', 'q', '\\q']:
                print("Shutting down MLB Quant. Good luck with your bets!")
                break
            
            # Retry logic for 503 errors
            max_retries = 4
            response = None
            for attempt in range(max_retries):
                try:
                    response = chat.send_message(user_prompt)
                    break  # If it succeeds, break out of the retry loop
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg:
                        wait_time = 2 ** attempt  # Waits 1s, 2s, 4s, 8s
                        print(f"\n[🚨 CLOUD BOTTLENECK] Google servers at capacity. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"\n[API ERROR]: {error_msg}")
                        break
            
            if not response:
                continue

            # ReAct loop for function calling
            while response.function_calls:
                for function_call in response.function_calls:
                    func_name = function_call.name
                    args = function_call.args

                    if func_name == "execute_sql":
                        sql_result = self.execute_sql(args['query'])
                        print("[AGENT OBSERVATION] Data retrieved. Feeding back to LLM...")
                        
                        # Apply retry logic to tool feedback
                        for attempt in range(max_retries):
                            try:
                                response = chat.send_message(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": sql_result}
                                    )
                                )
                                break
                            except Exception as e:
                                if "503" in str(e):
                                    time.sleep(2 ** attempt)
                                else:
                                    break
                    elif func_name == "fetch_daily_value":
                        tool_result = self.fetch_daily_value()
                        print("[AGENT OBSERVATION] Daily value retrieved. Feeding back to LLM...")
                        for attempt in range(max_retries):
                            try:
                                response = chat.send_message(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": tool_result}
                                    )
                                )
                                break
                            except Exception as e:
                                if "503" in str(e):
                                    time.sleep(2 ** attempt)
                                else:
                                    break
                    elif func_name == "fetch_lineup_analysis":
                        tool_result = self.fetch_lineup_analysis()
                        print("[AGENT OBSERVATION] Lineup analysis retrieved. Feeding back to LLM...")
                        for attempt in range(max_retries):
                            try:
                                response = chat.send_message(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": tool_result}
                                    )
                                )
                                break
                            except Exception as e:
                                if "503" in str(e):
                                    time.sleep(2 ** attempt)
                                else:
                                    break
                    elif func_name == "refresh_data":
                        tool_result = self.refresh_data()
                        print("[AGENT OBSERVATION] Data refresh complete. Feeding back to LLM...")
                        for attempt in range(max_retries):
                            try:
                                response = chat.send_message(
                                    types.Part.from_function_response(
                                        name=func_name,
                                        response={"result": tool_result}
                                    )
                                )
                                break
                            except Exception as e:
                                if "503" in str(e):
                                    time.sleep(2 ** attempt)
                                else:
                                    break
            
            # Print final response
            if response.text:
                print(f"\nAgent: {response.text}\n")

def prompt_agent():
    """Entry point for the script."""
    agent = MLBAgent()
    agent.run()

if __name__ == "__main__":
    prompt_agent()
