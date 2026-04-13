# AgentCore Integration Guide

This document explains how AWS Bedrock AgentCore is used in this chatbot platform.

## What is AgentCore?

AWS Bedrock AgentCore is a managed service for deploying containerized AI agents:
- **Runtime**: Managed container execution environment 
- **Memory**: Short/Long term conversation memory persistence
- **Gateway**: Transforming existing APIs into managed MCP servers

**Key Documentation**:
- Runtime: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html
- Memory: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- Gateway: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html

## How AgentCore is Used

### 1. AgentCore Runtime

**Location**: `chatbot-app/agentcore/`

The Strands Agent is containerized and deployed as an AgentCore Runtime:

```python
# chatbot-app/agentcore/src/agent/agent.py
from strands import Agent
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

class ChatbotAgent:
    def __init__(self, session_id: str, user_id: str):
        self.agent = Agent(
            model=BedrockModel(model_id="claude-sonnet-4"),
            tools=[...],
            session_manager=AgentCoreMemorySessionManager(...)  # AgentCore Memory
        )
```

**Key Features**:
- Runs on AWS Bedrock AgentCore managed runtime 
- Integrated with AgentCore Memory for conversation persistence
- Turn-based session management to optimize API calls
- Local tools (Weather, Visualization, etc.) embedded in container
```

### 2. AgentCore Memory

AgentCore Memory automatically persists conversation history:

```python
# Automatic persistence via AgentCoreMemorySessionManager
memory_config = AgentCoreMemoryConfig(
    memory_arn="arn:aws:bedrock-agentcore:...:memory/mem-xxx",
    max_tokens=12000
)

session_manager = AgentCoreMemorySessionManager(
    session_id=session_id,
    memory_config=memory_config
)
```

**Benefits**:
- Conversation history persisted across sessions
- Cross-session user preferences retained
- Automatic token limit management

### 3. AgentCore Gateway

**Location**: `agent-blueprint/agentcore-gateway-stack/`

AgentCore Gateway provides standardized access to Lambda tools:

```
AgentCore Runtime (with SigV4 credentials)
           ↓
   AgentCore Gateway (AWS_IAM auth)
           ↓
   ┌──────┴───────┬────────┬─────────┬─────────┐
   ↓              ↓        ↓         ↓         ↓
Wikipedia      ArXiv    Google   Tavily    Finance
Lambda         Lambda   Lambda   Lambda    Lambda
```

**Benefits**:
- Secure access to external services (no credentials in Runtime)
- Centralized API key management via Secrets Manager
- Lambda-based tools with auto-scaling

## Key Files

| File | Purpose |
|------|---------|
| `chatbot-app/agentcore/src/agent/agent.py` | Main agent with AgentCore Memory integration |
| `chatbot-app/agentcore/src/agent/turn_based_session_manager.py` | Optimized memory persistence |
| `chatbot-app/agentcore/src/agent/gateway_mcp_client.py` | Gateway tool access |
| `agent-blueprint/agentcore-runtime-stack/` | Runtime deployment (CDK) |
| `agent-blueprint/agentcore-gateway-stack/` | Gateway + Lambda functions (CDK) |

## Further Reading

- AWS Bedrock AgentCore Documentation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- AgentCore Runtime: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html
- AgentCore Memory: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- AgentCore Gateway: https://docs.aws.amazon.com/bedrock-agentcore/latest/dev

---

For implementation details, see:
- **README.md**: Architecture overview and features
- **DEPLOYMENT.md**: Step-by-step deployment instructions
