import os
import requests
import json
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Create FastMCP server
mcp = FastMCP("Serper Search Server")

@mcp.tool()
def google_search(query: str, num: int = 10) -> str:
    """
    Performs a Google Search using the Serper API.
    Returns organic search results including titles, links, and snippets.
    """
    if not SERPER_API_KEY:
        return "Error: SERPER_API_KEY not found in environment variables."

    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "num": num
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("organic", [])
        if not results:
            return f"No results found for '{query}'."

        output = f"Google Search Results for '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get("title", "No Title")
            link = res.get("link", "#")
            snippet = res.get("snippet", "No snippet available.")
            output += f"{i}. {title}\n   Link: {link}\n   Snippet: {snippet}\n\n"
        
        return output

    except Exception as e:
        return f"Error performing search: {str(e)}"

@mcp.tool()
def search_news(query: str, num: int = 10) -> str:
    """
    Performs a Google News Search using the Serper API.
    """
    if not SERPER_API_KEY:
        return "Error: SERPER_API_KEY not found in environment variables."

    url = "https://google.serper.dev/news"
    payload = json.dumps({
        "q": query,
        "num": num
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("news", [])
        if not results:
            return f"No news found for '{query}'."

        output = f"Google News Results for '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get("title", "No Title")
            link = res.get("link", "#")
            snippet = res.get("snippet", "No snippet.")
            date = res.get("date", "Unknown date")
            source = res.get("source", "Unknown source")
            output += f"{i}. {title}\n   Source: {source} | Date: {date}\n   Link: {link}\n   Snippet: {snippet}\n\n"
        
        return output

    except Exception as e:
        return f"Error performing news search: {str(e)}"

if __name__ == "__main__":
    # Use SSE transport to allow cross-container communication
    mcp.run(transport="sse")
