FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY . .

# Run the server
# Note: MCP servers can run over stdio. 
# In a container, this means communicating via container's stdin/stdout.
CMD ["python", "mcp_server.py"]
