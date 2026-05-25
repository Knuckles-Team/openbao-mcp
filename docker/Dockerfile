FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .[all]

ENTRYPOINT ["python", "-m", "openbao_mcp.mcp_server"]
