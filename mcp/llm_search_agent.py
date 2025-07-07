"""
LLM-Powered Search Agent for Slack Message Search
Pure agent-based approach with YAML configuration
"""

import json
import logging
import os
import yaml
from typing import Dict, Optional, Any
from dataclasses import dataclass
from openai import AsyncOpenAI

from lib.config import config


@dataclass
class EnhancedQuery:
    """Agent-enhanced search query"""
    search_params: Dict[str, Any]
    reasoning: str


class LLMSlackSearchAgent:
    """Pure LLM-powered agent for search query enhancement"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from YAML
        self.config = self._load_config()
        self.system_prompt = self.config["system_prompt"]
        
        # Model settings from YAML
        model_config = self.config.get("model", {})
        self.model_name = model_config.get("name", "gpt-4o-mini")
        self.temperature = model_config.get("temperature", 0.1)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
        # Metadata
        self.agent_info = self.config.get("agent", {})
        self.cost_info = self.config.get("cost", {})
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_prompt.yaml")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    async def enhance_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> EnhancedQuery:
        """Use LLM agent to enhance search query"""
        # Build user message
        user_message = f"User Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"
        
        # Let the agent handle everything
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Parse agent response
        response_text = response.choices[0].message.content.strip()
        enhancement_data = json.loads(response_text)
        
        return EnhancedQuery(
            search_params=enhancement_data["search_params"],
            reasoning=enhancement_data["reasoning"]
        )
    
def create_llm_search_agent():
    """Create an LLM-powered search agent"""
    return LLMSlackSearchAgent() 