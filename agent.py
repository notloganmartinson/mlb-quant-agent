import os
import sqlite3
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from core.db_manager import MLBDbManager

load_dotenv()

class MLBAgent:
    def __init__(self, db_path=None):
        """
        Initializes the MLB Quant Agent with Dependency Injection for the database.
        """
        self.db_path = db_path or os.environ.get("MLB_DB_PATH", "data/mlb_betting.db")
        self.db_manager = MLBDbManager(self.db_path)
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model_id = 'gemini-2.5-flash'

    def execute_sql(self, query: str) -> str:
        """
        Executes a read-only SQL query against the mlb_betting SQLite database.
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
        """Pulls the exact table structures directly from SQLite using the injected manager."""
        sql = "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        try:
            schemas = self.db_manager.query_agent_data(sql)
            # Join all the CREATE TABLE statements into one clean string
            return "\n\n".join([s['sql'] for s in schemas if s.get('sql')])
        except Exception as e:
            return f"Error retrieving schema: {e}"

    def _get_config(self):
        """Builds the agent configuration with tools and dynamic system instruction."""
        return types.GenerateContentConfig(
            tools=[self.execute_sql],
            system_instruction=(
                "You are a ruthless, quantitative MLB betting analyst. "
                "You have access to a local SQLite database containing advanced sabermetrics (SIERA, ISO, K-BB%, Bullpen metrics, Platoon Splits, Live Betting Markets, and Weather data). "
                f"You must query the SQLite database using this exact live schema:\n\n{self.get_live_schema()}\n\n"
                "If a user asks about the 'active slate', 'matchups', 'today', or 'tonight', you MUST filter the query by joining the stats table with the betting_markets table to ensure you only analyze players actively participating in upcoming games."
                "Always filter queries to pitchers with IP > 10."
                "Base all recommendations on cold, hard math. Never guess stats."
            )
        )

    def run(self):
        """Starts the ReAct loop for the agent."""
        print(f"MLB Quant Initialized (DB: {self.db_path}). Type '\\q' to quit.\n")
        
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
            
            # Print final response
            if response.text:
                print(f"\nAgent: {response.text}\n")

def prompt_agent():
    """Entry point for the script."""
    agent = MLBAgent()
    agent.run()

if __name__ == "__main__":
    prompt_agent()
