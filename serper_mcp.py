import os
import requests
import json
from fastmcp import FastMCP
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

if GROQ_API_KEY:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
    )
else:
    client = None

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
def visit_url(url: str, query: str) -> str:
    """
    Visits a web page to extract its text content, then uses an LLM to compress 
    the text, extracting only sentences directly relevant to the query.
    """
    if not SERPER_API_KEY:
        return "Error: SERPER_API_KEY not found in environment variables."
        
    scrape_url = "https://scrape.serper.dev"
    payload = {"url": url}
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", scrape_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        document = data.get("text", "")
        if not document:
            return f"No text content found at URL: {url}"

        # Context Compression Logic
        if not client:
            return "Error: GROQ_API_KEY not configured for context compression."
            
        system_prompt = """
        You are a Context Compressor for a RAG pipeline.
        Extract ONLY the exact sentences or phrases from the document that are directly relevant to answering the user's query.
        Do NOT summarize. Do NOT add new information.
        If no relevant information is found, output "No relevant context found."
        """
        llm_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocument:\n{document}"},
            ],
            temperature=0,
        )
        return llm_response.choices[0].message.content

    except Exception as e:
        return f"Error visiting URL {url}: {str(e)}"

app = mcp.http_app()

