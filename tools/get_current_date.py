from langchain.tools import tool
from datetime import datetime

@tool("get_current_date")
def get_current_date() -> dict:
    """Get the current date in the format YYYY-MM-DD."""
    return {
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "current_day": datetime.now().strftime("%A")
    } 
