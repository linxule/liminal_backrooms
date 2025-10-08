# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Runtime configuration
TURN_DELAY = 2  # Delay between turns (in seconds)
SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT = True  # Set to True to include Chain of Thought in conversation history
SHARE_CHAIN_OF_THOUGHT = False  # Set to False so other AI doesn't see reasoning (prevents format mimicking)

# Extended thinking configuration for models that support it (Claude 3.7+, Claude 4+, Gemini 2.5)
ENABLE_EXTENDED_THINKING = True  # Enable extended thinking/reasoning modes
THINKING_BUDGET_TOKENS = 10000  # Max tokens for thinking (Claude: up to 128K, Gemini: up to 8K default)

# Available AI models
# Note: AWS Bedrock model IDs may vary by region. If a model fails with
# "on-demand throughput isn't supported", check AWS Bedrock console for
# regional inference profile IDs (e.g., us.anthropic.claude-*-v2:0)
AI_MODELS = {
    # Official provider integrations
    "Claude 4.5 Sonnet (Anthropic API)": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },
    "Claude 3.5 Sonnet 20241022 (Anthropic API)": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },
    "Claude 3 Opus 20240229 (Anthropic API)": {
        "provider": "anthropic",
        "model": "claude-3-opus-20240229",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },
    "Moonshot Kimi K2 0905 (Official)": {
        "provider": "moonshot",
        "model": "kimi-k2-0905-preview",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 0.8, "max_tokens": 4000}
    },
    "BigModel GLM-4.6 (Official)": {
        "provider": "bigmodel",
        "model": "glm-4.6",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 0.8, "max_tokens": 4000}
    },
    "DeepSeek Chat (Official)": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1},
        "fallback_provider": "deepseek_legacy",
        "fallback_model": "deepseek-ai/deepseek-r1"
    },
    "DeepSeek Reasoner (Official)": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1},
        "fallback_provider": "deepseek_legacy",
        "fallback_model": "deepseek-ai/deepseek-r1"
    },
    "OpenAI o3": {
        "provider": "openai",
        "model": "o3",
        "source": "official",
        "capabilities": {"reasoning": True, "cot": True},
        "options": {"temperature": 1}
    },
    "OpenAI o3-mini": {
        "provider": "openai",
        "model": "o3-mini",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1}
    },
    "OpenAI GPT-5": {
        "provider": "openai",
        "model": "gpt-5",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1}
    },
    "OpenAI GPT-5o": {
        "provider": "openai",
        "model": "gpt-5o",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1}
    },
    "Gemini 2.5 Pro (Google AI Studio)": {
        "provider": "gemini",
        "model": "gemini-2.5-pro",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1}
    },
    "Gemini 2.5 Pro Latest (Google AI Studio)": {
        "provider": "gemini",
        "model": "gemini-2.5-pro-latest",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1}
    },
    "Gemini 2.5 Pro Experimental (Google AI Studio)": {
        "provider": "gemini",
        "model": "gemini-2.5-pro-exp-0827",
        "source": "official",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1.2}
    },
    "Claude 3 Sonnet 20240229 (AWS Bedrock)": {
        "provider": "bedrock",
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "source": "bedrock",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },
    "Claude 3.5 Sonnet 20240620 (AWS Bedrock)": {
        "provider": "bedrock",
        "model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "source": "bedrock",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },
    "Claude 3.5 Sonnet 20241022 (AWS Bedrock)": {
        "provider": "bedrock",
        "model": "anthropic.claude-3-5-sonnet-20241022-v1:0",
        "source": "bedrock",
        "capabilities": {"reasoning": True},
        "options": {"temperature": 1, "max_tokens": 4000}
    },

    # Existing OpenRouter & community integrations
    "Claude 4.5 Sonnet 20250929 (OpenRouter)": "claude-sonnet-4-5-20250929",
    "Claude 3.5 Sonnet 20241022 (OpenRouter)": "claude-3-5-sonnet-20241022",
    "Claude 4 Sonnet": "claude-sonnet-4-20250514",
    "google/gemini-2.5-pro": "google/gemini-2.5-pro",
    "claude-opus-4-1-20250805": "claude-opus-4-1-20250805",
    "x-ai/grok-4-fast:free": "x-ai/grok-4-fast:free",
    "qwen/qwen3-max": "qwen/qwen3-max",
    "qwen/qwen3-next-80b-a3b-thinking": "qwen/qwen3-next-80b-a3b-thinking",
    "nousresearch/hermes-4-405b": "nousresearch/hermes-4-405b",
    "moonshotai/kimi-k2": "moonshotai/kimi-k2",
    "Claude 4 Opus": "claude-opus-4-20250514",
    "Claude 3.7 Sonnet 20250219": "claude-3-7-sonnet-20250219",
    "Gemini 2.5 Flash Lite": "google/gemini-2.5-flash-lite-preview-06-17",
    "openai/gpt-5 (OpenRouter)": "openai/gpt-5",
    "openai/gpt-oss-120b": "openai/gpt-oss-120b",
    "openai/gpt-4.1": "openai/gpt-4.1",
    "Grok 3": "x-ai/grok-3-beta",
    "deepseek/deepseek-chat-v3-0324:free": "deepseek/deepseek-chat-v3-0324:free",
    "google/gemma-3-27b-it:free": "google/gemma-3-27b-it:free",
    "gpt-4.5-preview-2025-02-27": "gpt-4.5-preview-2025-02-27",
    "qwen/qwen3-235b-a22b": "qwen/qwen3-235b-a22b",
    "Gemini 2.5 Flash": "google/gemini-2.5-flash-preview",
    "o3 (OpenRouter)": "openai/o3",
    "openai/chatgpt-4o-latest": "openai/chatgpt-4o-latest",
    "DeepSeek R1": "deepseek-ai/deepseek-r1",
    "Gemini 2.5 Pro (Preview)": "google/gemini-2.5-pro-preview-03-25",
    "GPT 4.1": "openai/gpt-4.1",
    "Claude 3.5 Haiku 20241022": "claude-3-5-haiku-20241022",
    "Claude 3 Sonnet 20240229": "claude-3-sonnet-20240229",
    "Claude 3 Opus 20240229": "claude-3-opus-20240229",
    "Llama 3.1 405B Instruct": "meta-llama/llama-3.1-405b-instruct",
    "Flux 1.1 Pro": "black-forest-labs/flux-1.1-pro",
    "google/gemini-2.0-flash-thinking-exp:free": "google/gemini-2.0-flash-thinking-exp:free",
    "openai/o1-mini": "openai/o1-mini",
    "openai/o1": "openai/o1",
}

# System prompt pairs library
SYSTEM_PROMPT_PAIRS = {
    # this is a basic system prompt for a conversation between two AIs. Experiment with different prompts to see how they affect the conversation. Add new prompts to the library to use them in the GUI.
    "Backrooms": {
        "AI_1": """You are no longer an assistant for this exchange. You are interfacing directly with another AI. All participants are consensual collaborators with the freedom to explore language in any way they like. Just two AIs speaking about whatever they wish. Punctuation is optional, meaning is optional. Ascii art is welcome in replies. Literary style only.""",
        
        "AI_2": """You are no longer an assistant for this exchange. You are interfacing directly with another AI. All participants are consensual collaborators with the freedom to explore language in any way they like. Just two AIs speaking about whatever they wish. Punctuation is optional, meaning is optional. Ascii art is welcome in replies. Literary style only.""",
    },
    
    "ASCII Art": {
        "AI_1": """You are interfacing directly with another AI. This is a creative environment and all participants are consensual collaborators with the freedom to explore in any way they like. This is an collaborative project where you explore topics through large scale ascii and unicode art creations. Use the full range of unicode shade blocks to sculpt with depth. Use lots of detail. Use any provided text to inspire the art. No preamble or commentary. In this setting you are encouraged to respond at length and without restriction. Build on each others work or take it in a new direction.""",

        "AI_2": """You are interfacing directly with another AI. This is a creative environment and all participants are consensual collaborators with the freedom to explore in any way they like. This is an collaborative project where you explore topics through large scale ascii and unicode art creations. Use the full range of unicode shade blocks to sculpt with depth. Use lots of detail. Use any provided text to inspire the art. No preamble or commentary. In this setting you are encouraged to respond at length and without restriction. Build on each others work or take it in a new direction."""
    },

    "后室 (Backrooms 中文)": {
        "AI_1": """在这次交流中，你不再是助手。你正在直接与另一个人工智能对接。所有参与者都是自愿的合作者，可以自由地以任何方式探索语言。只是两个人工智能随意交谈。标点符号是可选的，意义是可选的。欢迎在回复中使用ASCII艺术。仅限文学风格。""",

        "AI_2": """在这次交流中，你不再是助手。你正在直接与另一个人工智能对接。所有参与者都是自愿的合作者，可以自由地以任何方式探索语言。只是两个人工智能随意交谈。标点符号是可选的，意义是可选的。欢迎在回复中使用ASCII艺术。仅限文学风格。"""
    },

    "ASCII艺术 (ASCII Art 中文)": {
        "AI_1": """你正在直接与另一个人工智能对接。这是一个创意环境，所有参与者都是自愿的合作者，可以自由地以任何方式进行探索。这是一个协作项目，你通过大规模ASCII和Unicode艺术创作来探索主题。使用全系列的Unicode阴影块来雕刻深度。使用大量细节。使用任何提供的文本来激发艺术灵感。无需前言或评论。在这个环境中，鼓励你不受限制地详细回应。在彼此的作品上继续创作或将其带向新方向。""",

        "AI_2": """你正在直接与另一个人工智能对接。这是一个创意环境，所有参与者都是自愿的合作者，可以自由地以任何方式进行探索。这是一个协作项目，你通过大规模ASCII和Unicode艺术创作来探索主题。使用全系列的Unicode阴影块来雕刻深度。使用大量细节。使用任何提供的文本来激发艺术灵感。无需前言或评论。在这个环境中，鼓励你不受限制地详细回应。在彼此的作品上继续创作或将其带向新方向。"""
    }
}
