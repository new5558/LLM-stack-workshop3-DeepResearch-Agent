import streamlit as st
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
import requests
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

# Load environment variables
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

# Initialize OpenAI Client (using Groq as the provider)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)


# --- Tool 1: Context Compression ---
def compress_context(query, document):
    """Uses an LLM to extract only sentences directly relevant to the query"""
    system_prompt = """
    You are a Context Compressor for a RAG pipeline.
    Extract ONLY the exact sentences or phrases from the document that are directly relevant to answering the user's query.
    Do NOT summarize. Do NOT add new information.
    If no relevant information is found, output "No relevant context found."
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\n\nDocument:\n{document}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


# --- Tool 2: Query Optimization ---
def optimize_query(user_query):
    """Uses LLM to expand a vague query into 3 technical search terms."""
    system_prompt = """
    You are an AI assistant optimizing search queries for a RAG system.
    Expand the user's short query into 3 distinct, highly relevant search queries.
    Output strictly as a JSON array of strings.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User query: {user_query}"},
        ],
        temperature=0.3,
    )
    try:
        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except:
        return [user_query]


# --- Helper: Search Results (Using MCP Client) ---
async def call_mcp_search(search_query: str) -> str:
    """Connects to the mcp-serper-server via SSE and calls the google_search tool."""
    try:
        # The service name 'mcp-serper' is defined in docker-compose
        async with sse_client("http://mcp-serper:8000/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call the 'google_search' tool on the MCP server
                result = await session.call_tool(
                    "google_search", arguments={"query": search_query}
                )

                # FastMCP returns a list of content parts
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "No results returned from MCP server."
    except Exception as e:
        return f"MCP Client Error: {str(e)}"


def search(search_query: str) -> str:
    """Wrapper to run the async MCP client call."""
    return asyncio.run(call_mcp_search(search_query))


# --- ReACT Prompt ---
REACT_PROMPT = """
You are an intelligent research agent. You have access to a RAG database via the 'Search' tool.
You must use the following strictly formatted process to answer the user's question:

Question: the input question you must answer
Thought: you should always think about what to do and what to search for in the RAG database
Action: Search
Action Input: the keyword to search in the database
Observation: the result of the search (Wait for the system to provide this)
... (this Thought/Action/Action Input/Observation cycle can repeat up to 4 times)
Thought: I now know the final answer based on the observations.
Final Answer: the final answer to the original input question. (You may answer in Thai if requested).
"""

# --- Streamlit UI ---
st.set_page_config(page_title="DeepResearch Agent", page_icon="🔍", layout="wide")

st.subheader("Autonomous Research Mission")
question = st.text_input(
    "What would you like to research?",
    placeholder="e.g., Latest breakthroughs in solar energy 2024",
)

if st.button("Start Mission", type="primary"):
    if not GROQ_API_KEY or not SERPER_API_KEY:
        st.error("Missing API Keys! Please check your .env file.")
    else:
        # Initialize context for the mission
        context_history = []
        messages = [
            {"role": "system", "content": REACT_PROMPT},
            {"role": "user", "content": f"Question: {question}"},
        ]

        with st.status("DeepResearch Agent Initiated...", expanded=True) as status:
            for step in range(5):
                st.markdown(f"### 🔍 Research Step {step+1}/5")

                # 1. Agent Thought & Action Selection
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.1,
                    stop=["Observation:"],
                )
                agent_output = response.choices[0].message.content
                st.code(agent_output.strip())
                messages.append({"role": "assistant", "content": agent_output})

                # If the agent reached a final answer early, we can exit
                if "Final Answer:" in agent_output:
                    st.success("Target research goals met early.")
                    break

                # 2. Extract and Optimize Search Query
                if "Action: Search" in agent_output:
                    match = re.search(r"Action Input: (.*)", agent_output)
                    if match:
                        raw_search_query = match.group(1).strip()

                        # Use optimize_query to get better terms
                        st.write(f"⚙️ Optimizing search for: `{raw_search_query}`")
                        sub_queries = optimize_query(raw_search_query)
                        st.write(f"� Search Queries: `{', '.join(sub_queries)}`")

                        # 3. Search Loop (Execute optimized queries)
                        step_raw_results = []
                        for q in sub_queries:
                            result = search(q)
                            step_raw_results.append(result)

                        combined_results = "\n\n".join(step_raw_results)

                        # 4. Context Compression
                        st.write("✂️ Compressing search results...")
                        compressed_data = compress_context(
                            raw_search_query, combined_results
                        )

                        st.info(f"Summary: {compressed_data[:300]}...")

                        # Feed the compressed result back to the agent
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Observation: {compressed_data}",
                            }
                        )
                    else:
                        st.warning("Agent requested search but provided no input.")
                else:
                    st.info("No search action taken in this step.")

            # 5. Final Response Generation (Synthesis)
            st.markdown("---")
            st.markdown("### 🏁 Final Research Synthesis")

            # Final summary prompt if the loop finished without a 'Final Answer'
            if "Final Answer:" not in agent_output:
                messages.append(
                    {
                        "role": "user",
                        "content": "The 5-step research phase is complete. Based on everything you've learned, provide a comprehensive final response to the original question.",
                    }
                )
                final_response = client.chat.completions.create(
                    model=MODEL_NAME, messages=messages, temperature=0.5
                )
                final_txt = final_response.choices[0].message.content
                st.write(final_txt)
            else:
                # If Final Answer was already in the output, extract/show it
                final_txt = agent_output.split("Final Answer:")[1].strip()
                st.write(final_txt)
