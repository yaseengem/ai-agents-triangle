# Strands Agent Chatbot - Deployment Guide

## Architecture Overview

```
Browser
  │
  ▼
Frontend + BFF (ECS Fargate)
  │ Next.js + API Routes
  │ @aws-sdk/client-bedrock-agentcore
  │
  ▼ InvokeAgentRuntimeCommand
AWS Bedrock AgentCore Runtime
  │ (Managed Service)
  │ Runtime ARN: arn:aws:bedrock-agentcore:...
  │
  ├─ Agent Core Container (ECR)
  │  └─ FastAPI + Strands Agent
  │     ├─ Calculator
  │     ├─ Weather
  │     ├─ Visualization
  │     ├─ Web Search
  │     └─ URL Fetcher
  │
  └─> MCP Servers (Lambda + ECS)
```

## Quick Start

### Prerequisites

- Docker Desktop running
- AWS CLI configured (`aws configure`)
- Node.js 20+
- Python 3.12+

### One-Command Deployment

```bash
cd agent-blueprint
./deploy.sh
```

### Deployment Options

When you run `./deploy.sh`, you'll see:

```
========================================
  Strands Agent Chatbot - Deployment
========================================

Select AWS Region:
  1) us-east-1      (US East - N. Virginia)
  2) us-west-2      (US West - Oregon) [default]
  ...

What would you like to deploy?
  1) AgentCore Runtime      (Agent container on Bedrock AgentCore)
  2) Frontend + BFF         (Next.js + CloudFront + ALB)
  3) MCP Tools              (AgentCore Gateway + Lambda functions)
  4) AgentCore Runtime A2A  (Report Writer Agent, etc.)
  5) Runtime + Frontend     (1 + 2 combined)
  6) Full Stack             (All components)

  0) Exit
```

## Configuration

### Parameter Store

After deployment, the following parameters are available:

```
/strands-agent-chatbot/dev/agentcore/runtime-arn
/strands-agent-chatbot/dev/agentcore/runtime-id
/mcp/endpoints/serverless/*
/mcp/endpoints/stateful/*
```

## Local Development

### Test Agent Core Locally

```bash
cd ../chatbot-app
./setup.sh

./start.sh
```

Visit http://localhost:3000

## Troubleshooting

### Docker not running

```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### AWS CLI not configured

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region: us-west-2
# Enter default output format: json
```

### CDK not bootstrapped

```bash
cd agentcore-runtime-stack
npx cdk bootstrap aws://ACCOUNT-ID/REGION
```

## Cleanup

To remove all resources:

```bash
cd agent-bluepirnt/
./destroy.sh
```

## Support

For issues:
1. Check CloudWatch Logs: `/aws/bedrock-agentcore/{runtime-id}`
2. Check ECS Task Logs: `/ecs/strands-agent-chatbot`
3. Review deployment output for specific error messages
