from langchain_core.tools import tool
from sqlalchemy import create_engine, text, Engine
import pandas as pd
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from typing import Annotated
from langchain_core.messages import ToolMessage
import os
from dotenv import load_dotenv
load_dotenv()

class ServerSession:
    """Server side state management for the database connection."""

    def __init__(self):
        self.engine: Engine = None
        self.df : pd.DataFrame = None

        self.engine = self.connect_engine()

    def connect_engine(self):

        if self.engine is None:

            #set up SQLAlchemy engine for session pooling with Supabasse

            _engine = create_engine(os.getenv("SUPABASE_URL"),
                       pool_size=5,
                       max_overflow=5,
                       pool_timeout=10,
                       pool_recycle=1800,
                       pool_pre_ping=True,
                       pool_use_lifo=True,
                       connect_args={
                           "application_name": "Analyst_agent",
                           "options":"-c statement_timeout=30000",
                           "keepalives":1,
                            "keepalives_idle":60,
                            "keepalives_interval":30,
                            "keepalives_count":3

                       })

            return _engine

        return self.engine

        
session = ServerSession()

@tool
def query_database(sql: str) -> str:
    """Execute a SQL query on the database and return results as a markdown table.
    
    Args: 
        sql (str): The SQL query to execute. Must be valid SQL that can be executed on the database directly.
    Returns:
        str: The results of the query as a markdown table.
    """
    try:
        with session.engine.connect() as conn:
            result = conn.execute(text(sql))

            columns = list(result.keys())
            rows = result.fetchall()

            df = pd.DataFrame(rows, columns=columns)
            session.df = df  # Store the DataFrame in the session for later use
            conn.close()
        return df.to_markdown(index=False)
    except Exception as e:
        return f"Error during query execution: {str(e)}"


@tool
def generate_visualization(name:str,sql_query:str,plotly_code:str,tool_call_id:Annotated[str, InjectedToolCallId]) -> str:
    '''Generate a visualization using Python, SQL, and Plotly. If the visualizaton is successfully generated, it's automatically rendered for the user on the frontend.

    Args:
        name: The name of the visualization. Should be a short name with underscores and no spaces.
        sql_query: The SQL query to retrieve data for the visualization. Must be a valid postgres SQL string that can be executed directly. The query will be executed and the result will be loaded into a DataFrame named 'df'.
        plotly_code: Python code that generates a Plotly figure. The code should create a variable named 'fig' that contains the Plotly figure object.

    Returns:
        str: Success message if successful or an error message.

    ## Assumptions
    Assume the data is already loaded into a DataFrame named 'df' and the following libraries are already imported for immediate use: 
    
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import plotly

    ## Example:
    User asks "Show me the top 5 creators by revenue"

    sql_query = "SELECT c.id, c.first_name, c.last_name, SUM(t.amount_usd) AS total_revenue\nFROM creators c\nJOIN transactions t ON c.id = t.creator_id\nGROUP BY c.id, c.first_name, c.last_name\nORDER BY total_revenue DESC\nLIMIT 5;"
    plotly_code = "fig = px.bar(df, x='first_name', y='total_revenue', title='Top 5 Creators by Revenue')\nfig.update_layout(xaxis_title='Creator', yaxis_title='Total Revenue ($)')"
    '''
    import io
    import os
    from contextlib import redirect_stdout, redirect_stderr

    os.makedirs("visualizations", exist_ok=True)

    file_path = f"visualizations/{name}.json"

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    pre_code = f'''
from sqlalchemy import text
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import plotly

# Generated SQL
df = pd.read_sql(text("""{sql_query}"""), engine)

# Generated plotly code
'''
    post_code = f'''

# Save the figure to JSON
if 'fig' in locals() or 'fig' in globals():
    fig_json = pio.to_json(fig)
    with open('{file_path}', 'w') as f:
        f.write(fig_json)
'''

    full_code = pre_code + plotly_code + post_code

    exec_globals ={}

    if "engine" in full_code: 
        exec_globals["engine"] = session.engine

    try:
        #Execute the code with visualization generation
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(full_code, exec_globals,{})

        #Get the captured output and errors
        print(f"STDOUT: \n\n{stdout_capture.getvalue()}\n")
        print(f"STDERR: \n\n{stderr_capture.getvalue()}\n")
        # Check if the fig was created
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                fig_json = f.read()
            return Command(
                update={
                    # update the state keys
                    "chart_json": fig_json,
                    # update the message history
                    "messages": [
                        ToolMessage(
                            "Visualization created successfully.", 
                            tool_call_id=tool_call_id
                        )
                    ],
                }
            )
        else:
            raise Exception(f"Error: Failed to generate visualization.\n\n<stderr>\n{stderr_capture.getvalue()}\n</stderr>")

    except Exception as e:
        # Get the error message
        error_message = str(e)
        return f"Error executing visualization code: {error_message}"