import json

# --- Planning LLM: has a start_research tool to hand off ---
START_RESEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "start_research",
        "description": "Call this function when the user is satisfied with the research plan and wants to begin the actual research. Pass the finalized research plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "research_plan": {
                    "type": "string",
                    "description": "The finalized, structured research plan agreed upon with the user."
                }
            },
            "required": ["research_plan"]
        }
    }
}

PLANNER_SYSTEM_PROMPT = """You are an interactive Research Planning Agent.
Your job is to help the user craft a detailed, step-by-step research plan.
- Infer the full research plan from user query.
- If user want to edit the plan edit as user suggested.
- However, ifuser explicitly says to start researching (e.g. "start", "go", "looks good, begin", "let's research"), call the `start_research` function with the final plan.
- Do NOT call start_research until the user explicitly confirms they want to begin.

Plan should be very concise but cover all aspect of the research.
example of the plan (your actual plan should also have similar characeter length with this example):
query:
What is OpenAI Deep Research?
plan:
(1) Search for information about OpenAI Deep Research to understand its overall definition, core capabilities, and primary purpose.
(2) Find official announcements, release notes, or technical papers from OpenAI regarding Deep Research to gather authoritative information.
(3) Investigate the technical mechanisms behind Deep Research, including:
(a) the underlying AI models utilized
(b) its autonomous browsing capabilities
(c) reasoning and synthesis steps
(4) Identify the target audience and primary use cases for the tool.
(5) Explore any known limitations, biases, or safety measures implemented by OpenAI for this feature.
(6) Compare Deep Research with standard AI web search tools to highlight its unique value proposition and differences in functionality.
(7) Determine the current availability, access requirements, and pricing model for Deep Research.
"""

def call_planner(sync_client, model_name: str, messages: list):
    """Calls the Planning LLM. Returns (content, tool_call_args_or_None)."""
    response = sync_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": PLANNER_SYSTEM_PROMPT}] + messages,
        tools=[START_RESEARCH_TOOL],
        tool_choice="auto",
        reasoning_effort='high',
        temperature=0.7,
    )
    msg = response.choices[0].message
    
    # Check if the planner wants to call start_research
    if msg.tool_calls:
        for tc in msg.tool_calls:
            if tc.function.name == "start_research":
                args = json.loads(tc.function.arguments)
                return msg.content, args.get("research_plan", "")
    
    return msg.content, None
