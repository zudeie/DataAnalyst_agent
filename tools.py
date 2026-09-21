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


