import streamlit as st
import os
import json
import asyncio
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import traceback
import requests

from planner import call_planner

# Load environment variables
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

# Initialize Sync Client for Chat
sync_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

async def run_autonomous_mission(user_query: str, status_container, messages_container):
    """
    Connects to the MCP server, fetches tools, and runs an autonomous Agent loop 
    using OpenAI's tool-calling format.
    """
    try:
        # Connect to the local MCP server container via SSE
        async with streamable_http_client("http://mcp-serper-server:8000/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Fetch tools from the MCP server
                mcp_tools_response = await session.list_tools()
                openai_tools = []

                # TODO: Convert MCP tools (mcp_tools_response) to OpenAI format (openai_tools)
                # Loop mcp_tools_response.tools and append to openai_tools
                
                status_container.write(f"🔌 Connected to MCP. Loaded {len(openai_tools)} tools.")
                
                messages = [
                    {"role": "system", "content": """You are an autonomous deep-research agent. You have access to tools to search the web and visit URLs.
You are given a research plan. Your job is to EXECUTE the plan by actively using your tools:
- Use `google_search` to find relevant information for each step of the plan.
- Use `visit_url` to scrape and read specific web pages for deeper context.
- After gathering enough information, synthesize a comprehensive final answer.

Do NOT just restate the plan. Actually perform the research by calling tools."""},
                    {"role": "user", "content": f"Execute the following research plan:\n\n{user_query}"}
                ]
                
                # Main Agent Loop (limit to prevent infinite loops)
                max_steps = 4
                for step in range(max_steps):
                    status_container.write(f"🧠 Agent Thinking (Step {step+1}/{max_steps})...")
                    
                    # Force a final answer without tools if we hit the last step
                    if step == max_steps - 1:
                        status_container.write("⚠️ Final step reached. Forcing final synthesis.")
                        
                        # TODO: Make message clear that this is final step. LLM should synthesize final answer now.
                        messages.append(...)
                        # TODO: Make sure that there will be no tool for LLm to call anymore
                        current_tool_choice = ...
                    
                    response = sync_client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice=current_tool_choice
                    )
                    
                    response_message = response.choices[0].message
                    messages.append(response_message)
                    
                    # Check if the LLM wants to call tools
                    if response_message.tool_calls:
                        for tool_call in response_message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            
                            status_container.write(f"🛠️ Executing MCP Tool: `{tool_name}` with args: `{tool_args}`")
                            
                            # Execute the tool via MCP
                            result = await session.call_tool(tool_name, arguments=tool_args)
                            
                            # Extract result text
                            tool_result_text = "\n".join([c.text for c in (result.content or []) if c.type == "text"])
                            
                            with st.expander(f"Tool Result: {tool_name}"):
                                st.text(tool_result_text[:1000] + "..." if len(tool_result_text) > 1000 else tool_result_text)
                            
                            # Append result back to conversation
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result_text
                            })
                    else:
                        # If no tool calls, it's a final response
                        status_container.update(label="✅ Mission Complete!", state="complete", expanded=False)
                        messages_container.markdown("### 🏁 Final Research Synthesis")
                        messages_container.write(response_message.content)
                        return
                
                status_container.update(label="⚠️ Reached maximum step limit.", state="error", expanded=False)

    except Exception as e:
        status_container.update(label="❌ Error running mission", state="error", expanded=False)
        st.error(f"Error: {e}")
        st.error(f"Traceback: {traceback.format_exc()}")


response = requests.get('http://mcp-serper-server:8000/')
st.write(response.text, 'response')

# --- Streamlit UI & Session State ---
st.set_page_config(page_title="DeepResearch Agent", page_icon="🔍", layout="wide")

if "phase" not in st.session_state:
    st.session_state.phase = "planning"

if "planner_messages" not in st.session_state:
    st.session_state.planner_messages = []

if "final_plan" not in st.session_state:
    st.session_state.final_plan = ""

st.subheader("Autonomous Research Mission")

if st.session_state.phase == "planning":
    st.markdown("### 📝 Research Planner")
    st.caption("Chat with the planner to build your research plan. When you're ready, tell it to start researching.")
    
    # Display the chat history
    for msg in st.session_state.planner_messages:
        if msg["role"] in ("user", "assistant"):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
            
    # Input box for user
    if user_input := st.chat_input("Describe your research topic..."):
        # Append user message
        st.session_state.planner_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # Call planner LLM
        with st.chat_message("assistant"):
            with st.spinner("Planning..."):
                content, research_plan = call_planner(sync_client, MODEL_NAME, st.session_state.planner_messages)
            
            if research_plan:
                # The planner decided to start research
                if content:
                    st.markdown(content)
                st.success("🚀 Research plan finalized! Starting autonomous research...")
                st.session_state.planner_messages.append({"role": "assistant", "content": content or "Starting research now."})
                st.session_state.final_plan = research_plan
                st.session_state.phase = "researching"
                st.rerun()
            else:
                st.markdown(content)
                st.session_state.planner_messages.append({"role": "assistant", "content": content})

elif st.session_state.phase == "researching":
    st.markdown("### 🔍 Autonomous Research Execution")
    
    st.button("⬅️ Back to Planner", on_click=lambda: st.session_state.update({"phase": "planning"}))
    
    with st.expander("Approved Research Plan", expanded=True):
        st.markdown(st.session_state.final_plan)
        
    if not GROQ_API_KEY:
        st.error("Missing GROQ_API_KEY in .env file.")
    else:
        status_container = st.status("DeepResearch Agent Initiated...", expanded=True)
        messages_container = st.container()
        
        async def main_flow():
            await run_autonomous_mission(st.session_state.final_plan, status_container, messages_container)
            
        asyncio.run(main_flow())
