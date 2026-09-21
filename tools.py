from langchain_core.tools import tool
from sqlalchemy import create_engine, text
import pandas as pd
import os

engine = create_engine(os.getenv("DATABASE_URL"))

@tool
def query_database(sql: str) -> str:
    """Execute a SQL query on the database and return results as a markdown table."""
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df.to_markdown(index=False)
    except Exception as e:
        return f"Error: {str(e)}"