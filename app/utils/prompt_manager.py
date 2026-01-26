"""
Dynamic context-aware prompt management for LLM interactions.

This module provides intelligent prompt truncation based on model context limits,
using balanced proportional allocation and smart summarization.
"""

import httpx
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

from app.components.base.config import get_settings

logger = logging.getLogger(__name__)

# Default context lengths for common models (fallback if API query fails)
DEFAULT_CONTEXT_LENGTHS = {
    "llama3.1": 131072,      # 128K context
    "llama3.1:latest": 131072,
    "llama3.1:8b": 131072,
    "llama3.1:70b": 131072,
    "llama3": 8192,
    "llama2": 4096,
    "phi3:mini": 4096,
    "phi3": 4096,
    "mistral": 8192,
    "mixtral": 32768,
    "all-minilm": 512,       # Embedding model
}

# Characters per token approximation (conservative estimate)
CHARS_PER_TOKEN = 4


@dataclass
class PromptAllocation:
    """Defines token allocation for different prompt sections."""
    system_prompt_ratio: float = 0.20    # 20% for system prompt
    requirement_ratio: float = 0.40       # 40% for current requirement
    historical_ratio: float = 0.40        # 40% for historical context
    output_reserve_ratio: float = 0.15    # Reserve 15% for output generation


@dataclass
class ManagedPrompt:
    """Result of prompt management with truncation metadata."""
    system_prompt: str
    user_prompt: str
    was_truncated: bool
    original_tokens: int
    final_tokens: int
    model_context_length: int
    truncation_details: Dict[str, Any]


class PromptManager:
    """
    Manages prompt construction with dynamic context-aware truncation.

    Features:
    - Queries model context length from Ollama API
    - Balanced proportional allocation (configurable ratios)
    - Smart summarization using LLM when truncation is needed
    - Reserves tokens for output generation

    Usage:
        manager = PromptManager()
        result = await manager.prepare_prompt(
            system_prompt="You are a helpful assistant...",
            requirement_text="Build a user authentication system...",
            historical_context="Previous TDD: ...",
            model_name="llama3.1:latest"
        )
    """

    _instance: Optional["PromptManager"] = None
    _model_context_cache: Dict[str, int] = {}

    def __init__(self, allocation: Optional[PromptAllocation] = None):
        self.settings = get_settings()
        self.allocation = allocation or PromptAllocation()
        self._summarization_prompt = self._get_summarization_prompt()

    @classmethod
    def get_instance(cls, allocation: Optional[PromptAllocation] = None) -> "PromptManager":
        """Get singleton instance of PromptManager."""
        if cls._instance is None:
            cls._instance = cls(allocation)
        return cls._instance

    async def get_model_context_length(self, model_name: Optional[str] = None) -> int:
        """
        Query the model's context length from Ollama API.

        Args:
            model_name: Model name to query (defaults to configured gen_model)

        Returns:
            Context length in tokens
        """
        model = model_name or self.settings.ollama_gen_model

        # Check cache first
        if model in self._model_context_cache:
            return self._model_context_cache[model]

        # Try to get from Ollama API
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/show",
                    json={"name": model}
                )
                if response.status_code == 200:
                    data = response.json()
                    # Parse model info for context length
                    model_info = data.get("model_info", {})

                    # Try different keys where context length might be stored
                    context_length = None
                    for key in model_info:
                        if "context" in key.lower():
                            context_length = model_info[key]
                            break

                    # Also check parameters
                    if context_length is None:
                        params = data.get("parameters", "")
                        if "num_ctx" in params:
                            # Parse num_ctx from parameters string
                            for line in params.split("\n"):
                                if "num_ctx" in line:
                                    try:
                                        context_length = int(line.split()[-1])
                                    except (ValueError, IndexError):
                                        pass

                    if context_length:
                        self._model_context_cache[model] = context_length
                        logger.info(f"Model {model} context length: {context_length}")
                        return context_length
        except Exception as e:
            logger.warning(f"Failed to query model context length: {e}")

        # Fallback to defaults
        for key, length in DEFAULT_CONTEXT_LENGTHS.items():
            if key in model.lower():
                self._model_context_cache[model] = length
                logger.info(f"Using default context length for {model}: {length}")
                return length

        # Ultimate fallback
        default = 4096
        self._model_context_cache[model] = default
        logger.warning(f"Using fallback context length for {model}: {default}")
        return default

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a conservative character-to-token ratio.
        For more accurate counting, consider using tiktoken.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN

    def tokens_to_chars(self, tokens: int) -> int:
        """Convert token count to approximate character count."""
        return tokens * CHARS_PER_TOKEN

    async def prepare_prompt(
        self,
        system_prompt: str,
        requirement_text: str,
        historical_context: str,
        model_name: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ) -> ManagedPrompt:
        """
        Prepare prompts with intelligent truncation if needed.

        Args:
            system_prompt: System instruction prompt
            requirement_text: Current requirement description
            historical_context: Historical TDDs, estimations, etc.
            model_name: Target model name (for context length lookup)
            user_prompt_template: Optional template with {requirement} and {historical} placeholders

        Returns:
            ManagedPrompt with potentially truncated content
        """
        model = model_name or self.settings.ollama_gen_model
        context_length = await self.get_model_context_length(model)

        # Calculate available tokens (excluding output reserve)
        available_tokens = int(context_length * (1 - self.allocation.output_reserve_ratio))

        # Estimate current token usage
        system_tokens = self.estimate_tokens(system_prompt)
        requirement_tokens = self.estimate_tokens(requirement_text)
        historical_tokens = self.estimate_tokens(historical_context)
        total_tokens = system_tokens + requirement_tokens + historical_tokens

        truncation_details = {
            "model": model,
            "context_length": context_length,
            "available_tokens": available_tokens,
            "original_system_tokens": system_tokens,
            "original_requirement_tokens": requirement_tokens,
            "original_historical_tokens": historical_tokens,
            "sections_truncated": [],
        }

        # Check if truncation is needed
        if total_tokens <= available_tokens:
            # No truncation needed
            user_prompt = self._build_user_prompt(
                requirement_text, historical_context, user_prompt_template
            )
            return ManagedPrompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                was_truncated=False,
                original_tokens=total_tokens,
                final_tokens=total_tokens,
                model_context_length=context_length,
                truncation_details=truncation_details,
            )

        # Truncation needed - apply balanced proportional allocation
        logger.info(f"Prompt truncation needed: {total_tokens} tokens > {available_tokens} available")

        # Calculate token budgets based on ratios
        system_budget = int(available_tokens * self.allocation.system_prompt_ratio)
        requirement_budget = int(available_tokens * self.allocation.requirement_ratio)
        historical_budget = int(available_tokens * self.allocation.historical_ratio)

        # Truncate each section as needed
        truncated_system = await self._truncate_section(
            system_prompt, system_tokens, system_budget, "system_prompt"
        )
        truncated_requirement = await self._truncate_section(
            requirement_text, requirement_tokens, requirement_budget, "requirement"
        )
        truncated_historical = await self._truncate_section(
            historical_context, historical_tokens, historical_budget, "historical"
        )

        # Track what was truncated
        if truncated_system != system_prompt:
            truncation_details["sections_truncated"].append("system_prompt")
        if truncated_requirement != requirement_text:
            truncation_details["sections_truncated"].append("requirement")
        if truncated_historical != historical_context:
            truncation_details["sections_truncated"].append("historical")

        # Calculate final token count
        final_tokens = (
            self.estimate_tokens(truncated_system) +
            self.estimate_tokens(truncated_requirement) +
            self.estimate_tokens(truncated_historical)
        )

        truncation_details["final_system_tokens"] = self.estimate_tokens(truncated_system)
        truncation_details["final_requirement_tokens"] = self.estimate_tokens(truncated_requirement)
        truncation_details["final_historical_tokens"] = self.estimate_tokens(truncated_historical)

        user_prompt = self._build_user_prompt(
            truncated_requirement, truncated_historical, user_prompt_template
        )

        return ManagedPrompt(
            system_prompt=truncated_system,
            user_prompt=user_prompt,
            was_truncated=True,
            original_tokens=total_tokens,
            final_tokens=final_tokens,
            model_context_length=context_length,
            truncation_details=truncation_details,
        )

    async def _truncate_section(
        self,
        content: str,
        current_tokens: int,
        budget_tokens: int,
        section_name: str,
    ) -> str:
        """
        Truncate a content section to fit within token budget.

        Uses smart summarization when truncation is needed.

        Args:
            content: Original content
            current_tokens: Current token count
            budget_tokens: Maximum allowed tokens
            section_name: Name of section (for logging)

        Returns:
            Truncated/summarized content
        """
        if current_tokens <= budget_tokens:
            return content

        logger.info(f"Truncating {section_name}: {current_tokens} -> {budget_tokens} tokens")

        # Calculate target character length
        target_chars = self.tokens_to_chars(budget_tokens)

        # For small reductions (<30%), use simple head truncation
        reduction_ratio = (current_tokens - budget_tokens) / current_tokens
        if reduction_ratio < 0.30:
            return self._head_truncate(content, target_chars)

        # For larger reductions, use smart summarization
        try:
            summarized = await self._smart_summarize(content, target_chars, section_name)
            if summarized and len(summarized) <= target_chars * 1.1:  # Allow 10% margin
                return summarized
        except Exception as e:
            logger.warning(f"Smart summarization failed for {section_name}: {e}")

        # Fallback to head truncation
        return self._head_truncate(content, target_chars)

    def _head_truncate(self, content: str, max_chars: int) -> str:
        """
        Truncate content from the end, keeping the beginning.

        Tries to break at paragraph or sentence boundaries.
        """
        if len(content) <= max_chars:
            return content

        truncated = content[:max_chars]

        # Try to break at paragraph boundary
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:  # Keep at least 70% of content
            return truncated[:last_para] + "\n\n[...truncated...]"

        # Try to break at sentence boundary
        for sep in [". ", ".\n", "! ", "? "]:
            last_sentence = truncated.rfind(sep)
            if last_sentence > max_chars * 0.8:
                return truncated[:last_sentence + 1] + " [...truncated...]"

        return truncated + "... [truncated]"

    async def _smart_summarize(
        self,
        content: str,
        target_chars: int,
        section_name: str,
    ) -> str:
        """
        Use LLM to intelligently summarize content.

        Args:
            content: Content to summarize
            target_chars: Target character length
            section_name: Type of content being summarized

        Returns:
            Summarized content
        """
        from app.utils.ollama_client import get_ollama_client

        target_words = target_chars // 5  # Approximate words

        summarize_prompt = f"""Summarize the following {section_name} content to approximately {target_words} words.
Preserve the most important technical details, key decisions, and critical information.
Keep the same format/structure where possible.

CONTENT TO SUMMARIZE:
{content}

SUMMARY (approximately {target_words} words):"""

        client = get_ollama_client()

        try:
            response, _ = await client.generate(
                system_prompt=self._summarization_prompt,
                user_prompt=summarize_prompt,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Summarization LLM call failed: {e}")
            raise

    def _get_summarization_prompt(self) -> str:
        """Get the system prompt for summarization."""
        return """You are a technical content summarizer. Your task is to condense technical documentation while preserving:
1. Key technical decisions and their rationale
2. Important module/component names
3. Critical requirements and constraints
4. Numerical data (hours, story points, estimates)
5. Dependencies and integration points

Be concise but complete. Maintain technical accuracy."""

    def _build_user_prompt(
        self,
        requirement: str,
        historical: str,
        template: Optional[str] = None,
    ) -> str:
        """Build the user prompt from components."""
        if template:
            return template.format(
                requirement=requirement,
                historical=historical,
                requirement_description=requirement,
                historical_context=historical,
            )

        return f"""REQUIREMENT:
{requirement}

HISTORICAL CONTEXT:
{historical}"""


def get_prompt_manager(allocation: Optional[PromptAllocation] = None) -> PromptManager:
    """Get singleton PromptManager instance."""
    return PromptManager.get_instance(allocation)
