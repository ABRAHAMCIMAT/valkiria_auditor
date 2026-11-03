"""
Lambda target for the AgentCore MCP Gateway. Exposes read-only access to the
ISO 27001 knowledge base to MCP clients authorized through the gateway.
"""
import json
import os

import boto3
from botocore.config import Config

# The Lambda timeout is 60 seconds
bedrock_agent = boto3.client(
    'bedrock-agent-runtime',
    config=Config(connect_timeout=5, read_timeout=45),
)

KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
DEFAULT_RESULTS = 5
MAX_RESULTS = 20


def query_knowledge_base(arguments):
    """Retrieve the passages most relevant to a query."""
    results = int(arguments.get('number_of_results', DEFAULT_RESULTS))
    response = bedrock_agent.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={'text': arguments['query']},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': max(1, min(results, MAX_RESULTS)),
            },
        },
    )
    return {
        'results': [
            {
                'text': item['content'].get('text', ''),
                'score': item.get('score'),
                'source': item.get('location', {}),
            }
            for item in response.get('retrievalResults', [])
        ],
    }


TOOLS = {'query_knowledge_base': query_knowledge_base}


def lambda_handler(event, context):
    """The gateway sends the tool arguments as the event and the tool name as <target>___<tool>."""
    full_name = context.client_context.custom['bedrockAgentCoreToolName']
    tool_name = full_name.split('___', 1)[-1]
    print(f"[INFO] Gateway tool call: {tool_name}")

    tool = TOOLS.get(tool_name)
    if tool is None:
        print(f"[WARN] Unknown gateway tool: {tool_name}")
        return {'error': f'Unknown tool: {tool_name}'}

    try:
        return json.loads(json.dumps(tool(event), default=str))
    except Exception as e:
        print(f"[ERROR] Gateway tool {tool_name} failed: {str(e)}")
        return {'error': f'{tool_name} failed'}
