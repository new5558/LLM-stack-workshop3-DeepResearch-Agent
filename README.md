# Workshop 3: DeepResearch Agent - Hybrid Stack

This workshop demonstrates a hybrid architecture combining **Model Context Protocol (MCP)** and a **Streamlit Web Application** for autonomous research.

## 🏗️ Architecture
- **MCP Server (`mcp-serper`)**: A backend service providing Google Search tools via Serper.
- **Web App (`deepresearch-webapp`)**: A user-friendly Streamlit frontend implementing the ReACT agent logic, query optimization, and context compression.

## 🚀 Getting Started

### 1. Configure API Keys
Add your keys to the `.env` file:
```env
GROQ_API_KEY=your_groq_key
SERPER_API_KEY=your_serper_key
```

### 2. Build and Run
Start both services:
```bash
docker-compose up --build
```

### 3. Access the Tools
- **DeepResearch Web App**: Open [http://localhost:8501](http://localhost:8501) in your browser.
- **Serper MCP Server**: This service runs in the background. You can test its stdio interface via:
  ```bash
  docker exec -i mcp-serper-server python serper_mcp.py
  ```

## 🛠️ Features
- **🚀 Agentic RAG**: Live ReACT agent loop showing Thoughts, Actions (Search), and Observations.
- **⚡ Query Optimizer**: Expand vague queries into technical search terms.
- **✂️ Context Compressor**: Save tokens by extracting only the most relevant sentences from documents.
