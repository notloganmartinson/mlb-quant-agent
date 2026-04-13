import os
import sqlite3
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Tools
def execute_sql(query: str) -> str:
  """
  Executes a read-only SQL query against the mlb_betting SQLite database.
  This is the agent's primary way to view stats and betting odds.
  """
  print(f"\n[TOOL CALL] Executing SQL: {query}")
  try:
    # Update path to the professional directory structure
    conn = sqlite3.connect('data/mlb_betting.db')
    cursor = conn.cursor()

    # Security check to prevent LLM from deleting tables
    if not query.strip().upper().startswith("SELECT"):
      return "Error: You are only allowed to run SELECT queries."

    cursor.execute(query)
    results = cursor.fetchall()

    # Format the output cleanly so LLM can read it
    if cursor.description:
      columns = [desc[0] for desc in cursor.description]
      formatted_data = [dict(zip(columns, row)) for row in results]
      conn.close()
      return str(formatted_data)
    else:
      conn.close()
      return "Query executed successfully, but returned no data."

  except Exception as e:
    return f"SQL Error: {str(e)}"

# helper function for system prompt so agent always has correct db schema
def get_live_schema() -> str:
    """Pulls the exact table structures directly from SQLite."""
    # Updated path to match structure
    conn = sqlite3.connect('data/mlb_betting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    schemas = cursor.fetchall()
    conn.close()
    
    # Join all the CREATE TABLE statements into one clean string
    return "\n\n".join([schema[0] for schema in schemas if schema[0]])

# Initialize the Brain: pass python function directly into tools array
# SDK automatically returns it into a JSON schema for the LLM
agent_config = types.GenerateContentConfig(
  tools=[execute_sql],
  system_instruction=(
    "You are a ruthless, quantitative MLB betting analyst. "
    "You have access to a local SQLite database containing advanced sabermetrics (SIERA, ISO, K-BB%, Bullpen metrics, Platoon Splits, Live Betting Markets, and Weather data). "
    f"You must query the SQLite database using this exact live schema:\n\n{get_live_schema()}\n\n"
    "If a user asks about the 'active slate', 'matchups', 'today', or 'tonight', you MUST filter the query by joining the stats table with the betting_markets table to ensure you only analyze players actively participating in upcoming games."
    "Always filter queries to pitchers with IP > 10."
    "Base all recommendations on cold, hard math. Never guess stats."
  )
)

# ReAct Loop
def prompt_agent():
  print("MLB Quant Initialized. Type '\\q' to quit.\n")
  # Init stateful chat session
  chat = client.chats.create(
    model='gemini-2.5-flash',
    config=agent_config
  )
  while True:
    user_prompt = input("> ")
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
                # If it's a different error, print it and stop
                print(f"\n[API ERROR]: {error_msg}")
                break
    
    if not response:
        continue

    # Custom While loop for tool calling (For learning the ReAct pattern)
    # PRO TIP: In production, can set 'automatic_function_calling=True'
    # in the GenerateContentConfig to handle this loop automatically.
    while response.function_calls:
      for function_call in response.function_calls:
        func_name = function_call.name
        args = function_call.args

        if func_name == "execute_sql":
          sql_result = execute_sql(args['query'])
          print("[AGENT OBSERVATION] Data retrieved. Feeding back to LLM...")
          
          # We apply the same retry logic to the tool-result feedback call
          for attempt in range(max_retries):
              try:
                  response = chat.send_message(
                    types.Part.from_function_response(
                      name=func_name,
                      response={"result":sql_result}
                    )
                  )
                  break
              except Exception as e:
                  if "503" in str(e):
                      time.sleep(2 ** attempt)
                  else:
                      break
    
    # Check if response has text (some turns only have function calls)
    if response.text:
        print(f"\nAgent: {response.text}\n")

if __name__ == "__main__":
  prompt_agent()
