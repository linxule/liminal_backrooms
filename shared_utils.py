# shared_utils.py

import base64
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import replicate
from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from together import Together
from typing import Any, Callable, Dict, List, Optional

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None

    class BotoCoreError(Exception):
        """Fallback BotoCoreError when botocore is unavailable."""

    class ClientError(Exception):
        """Fallback ClientError when botocore is unavailable."""
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("BeautifulSoup not found. Please install it with 'pip install beautifulsoup4'")

# Load environment variables
load_dotenv()

# Initialize Anthropic client with API key
anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Initialize OpenAI client lazily to support optional API key usage
openai_api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

# Cache for AWS Bedrock client
_bedrock_client = None


def get_bedrock_client():
    """Return a cached AWS Bedrock runtime client if available."""
    global _bedrock_client

    if _bedrock_client is not None:
        return _bedrock_client

    if not boto3:
        return None

    region = os.getenv("AWS_REGION", "us-east-1")
    try:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Failed to initialize AWS Bedrock client: {exc}")
        _bedrock_client = None

    return _bedrock_client


def format_reasoning_response(content, reasoning_blocks=None):
    """Format model responses with optional reasoning content."""
    cleaned_content = content or ""
    extracted_reasoning = []

    if isinstance(cleaned_content, str):
        # Capture <think> blocks for reasoning before removing them from the final content.
        extracted_reasoning = [
            match.strip()
            for _, match in re.findall(
                r'<(think|thinking)>(.*?)</\1>',
                cleaned_content,
                flags=re.DOTALL | re.IGNORECASE
            )
            if match and match.strip()
        ]
        cleaned_content = re.sub(
            r'<(think|thinking)>.*?</\1>',
            '',
            cleaned_content,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
    else:
        cleaned_content = str(cleaned_content)

    combined_reasoning = []
    if reasoning_blocks:
        combined_reasoning.extend(
            block.strip()
            for block in reasoning_blocks
            if isinstance(block, str) and block.strip()
        )
    if extracted_reasoning:
        combined_reasoning.extend(extracted_reasoning)

    reasoning_text = None
    if combined_reasoning:
        seen = set()
        deduped_reasoning = []
        for block in combined_reasoning:
            if block not in seen:
                deduped_reasoning.append(block)
                seen.add(block)
        reasoning_text = "\n".join(deduped_reasoning).strip() or None
    else:
        deduped_reasoning = []

    if not cleaned_content and reasoning_text:
        # Attempt to surface a succinct final answer from the reasoning text.
        final_answer_pattern = re.compile(r"(?:final\s+answer|answer)\s*[:\-]\s*(.+)", re.IGNORECASE)
        candidate = ""

        for block in reversed(deduped_reasoning):
            match = final_answer_pattern.search(block)
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    break

            for line in reversed(block.splitlines()):
                stripped_line = line.strip()
                if stripped_line:
                    candidate = stripped_line
                    break
            if candidate:
                break

        cleaned_content = candidate or reasoning_text

    result = {
        "content": cleaned_content,
    }
    if reasoning_text:
        result["reasoning"] = reasoning_text

    # Only import config when needed to avoid circular import issues
    from config import SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT

    if SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT:
        display_sections = []
        if reasoning_text:
            display_sections.append(f"[Chain of Thought]\n{reasoning_text}")
        if cleaned_content:
            display_sections.append(f"[Final Answer]\n{cleaned_content}")
        if display_sections:
            result["display"] = "\n\n".join(display_sections)
        else:
            result["display"] = cleaned_content
    elif not cleaned_content and reasoning_text:
        # Ensure downstream consumers never see an empty response when reasoning is present.
        result["content"] = reasoning_text

    return result


def build_error_response(message):
    """Return a standardized error response payload."""
    return {
        "role": "system",
        "content": str(message) if message else "An unknown error occurred"
    }


def normalize_response(response):
    """Normalize provider responses to a standard dict structure."""
    if response is None:
        return build_error_response("Provider returned no response")

    if isinstance(response, dict):
        normalized = dict(response)
        role = normalized.get("role", "assistant") or "assistant"
        content = normalized.get("content")

        if content is None and "error" in normalized:
            content = normalized["error"]
            role = "system"
        if content is None or (isinstance(content, str) and not content.strip()):
            # If content is empty but we have reasoning, use that instead
            if normalized.get("reasoning"):
                content = normalized.get("display") or normalized["reasoning"]
            else:
                content = ""

        # If still empty after all checks, flag as error
        if not content or (isinstance(content, str) and not content.strip()):
            if not normalized.get("reasoning"):
                return build_error_response("Provider returned no response")

        normalized["role"] = role
        normalized["content"] = content
        return normalized

    if isinstance(response, str):
        stripped = response.strip()
        if stripped.lower().startswith("error"):
            return build_error_response(stripped)
        return {
            "role": "assistant",
            "content": response
        }

    return {
        "role": "assistant",
        "content": str(response)
    }

def call_claude_api(prompt, messages, model_id, system_prompt=None, options=None):
    """Call the Claude API with the given messages and prompt"""
    options = options or {}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not found in environment variables"
    
    url = "https://api.anthropic.com/v1/messages"
    
    # Import config for extended thinking settings
    from config import ENABLE_EXTENDED_THINKING, THINKING_BUDGET_TOKENS

    # Ensure we have a system prompt
    payload = {
        "model": model_id,
        "max_tokens": options.get("max_tokens", 4000),
        "temperature": options.get("temperature", 1),
    }

    if "top_p" in options:
        payload["top_p"] = options["top_p"]
    if "stop_sequences" in options:
        payload["stop_sequences"] = options["stop_sequences"]

    # Enable extended thinking for supported models (Claude 3.7+, Claude 4+)
    if ENABLE_EXTENDED_THINKING and ("claude-3-7" in model_id.lower() or "claude-4" in model_id.lower()):
        payload["thinking"] = {
            "type": "enabled",
            "budget_tokens": THINKING_BUDGET_TOKENS
        }

    # Set system if provided
    if system_prompt:
        payload["system"] = system_prompt
        print(f"CLAUDE API USING SYSTEM PROMPT: {system_prompt}")
    
    # Clean messages to remove duplicates
    filtered_messages = []
    seen_contents = set()
    
    for msg in messages:
        # Skip system messages (handled separately)
        if msg.get("role") == "system":
            continue
            
        # Check for duplicates by content
        content = msg.get("content", "")
        if content in seen_contents:
            print(f"Skipping duplicate message in API call: {content[:30]}...")
            continue
            
        seen_contents.add(content)
        filtered_messages.append(msg)
    
    # Add the current prompt as the final user message
    filtered_messages.append({
        "role": "user",
        "content": prompt
    })

    # Add filtered messages to payload
    payload["messages"] = filtered_messages
    
    # Actual API call
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract both text and thinking content blocks
        thinking_blocks = []
        text_blocks = []

        if 'content' in data and len(data['content']) > 0:
            for content_item in data['content']:
                content_type = content_item.get('type')
                if content_type == 'thinking':
                    thinking_text = content_item.get('thinking', content_item.get('text', ''))
                    if thinking_text:
                        thinking_blocks.append(thinking_text)
                elif content_type == 'text':
                    text_blocks.append(content_item.get('text', ''))

        # Combine text blocks
        final_text = '\n'.join(text_blocks).strip()

        # Use format_reasoning_response to handle thinking + text
        if thinking_blocks or not final_text:
            return format_reasoning_response(final_text, thinking_blocks)

        return final_text if final_text else "No content in response"

    except Exception as e:
        return f"Error calling Claude API: {str(e)}"

def call_llama_api(prompt, conversation_history, model, system_prompt):
    # Only use the last 3 exchanges to prevent context length issues
    recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    
    # Format the conversation history for LLaMA
    formatted_history = ""
    for message in recent_history:
        if message["role"] == "user":
            formatted_history += f"Human: {message['content']}\n"
        else:
            formatted_history += f"Assistant: {message['content']}\n"
    formatted_history += f"Human: {prompt}\nAssistant:"

    try:
        # Stream the output and collect it piece by piece
        response_chunks = []
        for chunk in replicate.run(
            model,
            input={
                "prompt": formatted_history,
                "system_prompt": system_prompt,
                "max_tokens": 3000,
                "temperature": 1.1,
                "top_p": 0.99,
                "repetition_penalty": 1.0
            },
            stream=True  # Enable streaming
        ):
            if chunk is not None:
                response_chunks.append(chunk)
                # Print each chunk as it arrives
                # print(chunk, end='', flush=True)
        
        # Join all chunks for the final response
        response = ''.join(response_chunks)
        return response
    except Exception as e:
        print(f"Error calling LLaMA API: {e}")
        return None

def call_openai_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call OpenAI's official Responses API for reasoning-capable models."""
    if not openai_client:
        return "Error: OPENAI_API_KEY not found in environment variables"

    options = options or {}

    def to_text_content(text):
        if text is None:
            return ""
        if isinstance(text, list):
            return "\n".join(
                to_text_content(item) if not isinstance(item, str) else item
                for item in text
            ).strip()
        if not isinstance(text, str):
            return str(text)
        return text

    def build_content(role, text):
        stripped = to_text_content(text).strip()
        if not stripped:
            return []
        content_type = "output_text" if role == "assistant" else "input_text"
        return [{
            "type": content_type,
            "text": stripped
        }]

    messages = []
    if system_prompt:
        content_blocks = build_content("system", system_prompt)
        if content_blocks:
            messages.append({
                "role": "system",
                "content": content_blocks
            })

    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if not role:
            continue
        content_blocks = build_content(role, content)
        if not content_blocks:
            continue
        messages.append({
            "role": role,
            "content": content_blocks
        })

    user_content_blocks = build_content("user", prompt)
    if user_content_blocks:
        messages.append({
            "role": "user",
            "content": user_content_blocks
        })
    else:
        # Ensure the input is never empty; fall back to a placeholder prompt.
        messages.append({
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": "..."
            }]
        })

    try:
        response_kwargs = {
            "model": model,
            "input": messages  # Responses API uses 'input' not 'messages'
        }

        if "temperature" in options:
            response_kwargs["temperature"] = options["temperature"]
        if "top_p" in options:
            response_kwargs["top_p"] = options["top_p"]
        if "max_output_tokens" in options:
            response_kwargs["max_output_tokens"] = options["max_output_tokens"]

        response = openai_client.responses.create(**response_kwargs)

        final_text = getattr(response, "output_text", None)
        if isinstance(final_text, list):
            final_text = "\n".join(part for part in final_text if part).strip()
        elif final_text and isinstance(final_text, str):
            final_text = final_text.strip()

        if hasattr(response, "model_dump"):
            response_dict = response.model_dump()
        elif hasattr(response, "to_dict"):
            response_dict = response.to_dict()
        else:
            response_dict = json.loads(response.model_dump_json())

        reasoning_blocks = []
        # Attempt to use the convenience property if available
        if not final_text:
            final_text = response_dict.get("output_text")
            if isinstance(final_text, list):
                final_text = "\n".join(part for part in final_text if part).strip()
            elif isinstance(final_text, str):
                final_text = final_text.strip()

        output_blocks = response_dict.get("output") or []
        text_segments = []

        def append_reasoning_text(text):
            if not text:
                return
            cleaned = text.strip()
            if cleaned:
                reasoning_blocks.append(cleaned)

        def extract_reasoning(content_block, default_is_reasoning=False):
            if not isinstance(content_block, dict):
                if default_is_reasoning and isinstance(content_block, str):
                    append_reasoning_text(content_block)
                return

            block_type = (content_block.get("type") or "").lower()
            text = content_block.get("text")
            nested = content_block.get("content") if isinstance(content_block, dict) else None

            is_reasoning = default_is_reasoning or any(
                keyword in block_type
                for keyword in ("reason", "chain_of_thought", "cot")
            )

            if is_reasoning and text:
                append_reasoning_text(text)

            if isinstance(nested, dict):
                extract_reasoning(nested, default_is_reasoning=is_reasoning)
            elif isinstance(nested, list):
                for nested_block in nested:
                    extract_reasoning(nested_block, default_is_reasoning=is_reasoning)

        # Collect reasoning from explicit reasoning sections if provided
        reasoning_sections = response_dict.get("reasoning")
        if reasoning_sections:
            if isinstance(reasoning_sections, dict):
                reasoning_iterable = [reasoning_sections]
            elif isinstance(reasoning_sections, list):
                reasoning_iterable = reasoning_sections
            else:
                reasoning_iterable = []
            for section in reasoning_iterable:
                extract_reasoning(section, default_is_reasoning=True)

        if output_blocks:
            for block in output_blocks:
                if not isinstance(block, dict):
                    continue
                block_type = (block.get("type") or "").lower()
                block_content = block.get("content") or []
                if not isinstance(block_content, list):
                    block_content = [block_content]
                for content_block in block_content:
                    if content_block is None:
                        continue
                    if isinstance(content_block, dict):
                        lower_type = (content_block.get("type") or "").lower()
                        text = content_block.get("text", "")
                    else:
                        lower_type = ""
                        text = str(content_block)
                    if lower_type and any(keyword in lower_type for keyword in ("reason", "chain_of_thought", "cot")):
                        append_reasoning_text(text)
                    elif text:
                        text_segments.append(text)
                    extract_reasoning(content_block)

                # Some providers may embed reasoning directly on the block
                if block_type and any(keyword in block_type for keyword in ("reason", "chain_of_thought", "cot")):
                    extract_reasoning(block, default_is_reasoning=True)

        if not final_text:
            final_text = "\n".join(text_segments).strip()

        if not final_text and reasoning_blocks:
            final_text = reasoning_blocks[-1]

        result = format_reasoning_response(final_text, reasoning_blocks)
        return result

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return f"Error calling OpenAI API: {str(e)}"

def call_openrouter_api(messages, model, options=None):
    """Call the OpenRouter API to access various LLM models."""
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
            "X-Title": "AI Conversation"
        }

        options = options or {}
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": options.get("temperature", 1),
            "max_tokens": options.get("max_tokens", 4000)
        }

        if "top_p" in options:
            payload["top_p"] = options["top_p"]

        print("\nSending to OpenRouter:")
        print(f"Model: {model}")
        print(f"Messages: {json.dumps(messages, indent=2)}")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")

        if response.status_code == 200:
            response_data = response.json()
            print(f"Response data: {json.dumps(response_data, indent=2)}")

            if 'choices' in response_data and response_data['choices']:
                message = response_data['choices'][0].get('message', {})
                content = message.get('content', '') if isinstance(message, dict) else ''
                return format_reasoning_response(content, [])

            return {
                "role": "system",
                "content": "Error: Unexpected response structure from OpenRouter"
            }

        error_msg = f"OpenRouter API error {response.status_code}: {response.text}"
        print(error_msg)
        if response.status_code == 404:
            print("Model not found. Please check if the model name is correct.")
        elif response.status_code == 401:
            print("Authentication error. Please check your API key.")
        return {
            "role": "system",
            "content": error_msg
        }

    except requests.exceptions.Timeout:
        print("Request timed out. The server took too long to respond.")
        return {
            "role": "system",
            "content": "Error: Request to OpenRouter timed out"
        }
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return {
            "role": "system",
            "content": f"Error: Network error - {str(e)}"
        }
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        print(f"Error type: {type(e)}")
        return {
            "role": "system",
            "content": f"Error: {str(e)}"
        }

def call_replicate_api(prompt, conversation_history, model, gui=None):
    try:
        # Only use the prompt, ignore conversation history
        input_params = {
            "width": 1024,
            "height": 1024,
            "prompt": prompt
        }
        
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input=input_params
        )
        
        image_url = str(output)
        
        # Save the image locally
        image_dir = Path("images")
        image_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = image_dir / f"generated_{timestamp}.jpg"
        
        response = requests.get(image_url)
        with open(image_path, "wb") as f:
            f.write(response.content)
        
        if gui:
            gui.display_image(image_url)
        
        return {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I have generated an image based on your prompt."
                }
            ],
            "prompt": prompt,
            "image_url": image_url,
            "image_path": str(image_path)
        }
        
    except Exception as e:
        print(f"Error calling Flux API: {e}")
        return None


def call_deepseek_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call DeepSeek's official API for chat and reasoning models."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "Error: DEEPSEEK_API_KEY not found in environment variables"

    options = options or {}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if not content:
            continue
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
    }

    if "temperature" in options:
        payload["temperature"] = options["temperature"]
    if "max_tokens" in options:
        payload["max_tokens"] = options["max_tokens"]

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return "No content in DeepSeek response"

        message = choices[0].get("message", {})
        content = message.get("content", "") or ""

        # DeepSeek returns reasoning_content as a string, not an array
        reasoning_content = message.get("reasoning_content", "")
        reasoning_blocks = []
        if reasoning_content and isinstance(reasoning_content, str):
            reasoning_blocks.append(reasoning_content)
        elif isinstance(reasoning_content, list):
            # Handle array format if API changes in future
            for reasoning_item in reasoning_content:
                if isinstance(reasoning_item, str):
                    reasoning_blocks.append(reasoning_item)
                elif isinstance(reasoning_item, dict):
                    text = reasoning_item.get("text")
                    if text:
                        reasoning_blocks.append(text)

        # DeepSeek may embed <think> tags inside the final content;
        # format_reasoning_response handles stripping when needed.
        return format_reasoning_response(content, reasoning_blocks)

    except Exception as exc:  # pragma: no cover - network errors
        print(f"Error calling DeepSeek API: {exc}")
        return f"Error calling DeepSeek API: {str(exc)}"


def call_deepseek_via_replicate(prompt, conversation_history, model, system_prompt, options=None):
    """Call the DeepSeek model through Replicate API (legacy fallback)."""
    try:
        options = options or {}
        # Format messages for the conversation history
        formatted_history = ""
        if system_prompt:
            formatted_history += f"System: {system_prompt}\n"
        
        # Add conversation history ensuring proper interleaving
        last_role = None
        for msg in conversation_history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Skip if same role as last message
                if role == last_role:
                    continue
                    
                if isinstance(content, str):
                    formatted_history += f"{role.capitalize()}: {content}\n"
                    last_role = role
        
        # Add current prompt
        formatted_history += f"User: {prompt}\n"
        
        print(f"\nSending to DeepSeek via Replicate:")
        print(f"Formatted History:\n{formatted_history}")
        
        # Make API call
        output = replicate.run(
            "deepseek-ai/deepseek-r1",
            input={
                "prompt": formatted_history,
                "max_tokens": options.get("max_tokens", 8000),
                "temperature": options.get("temperature", 1)
            }
        )
        
        # Collect the response - ensure we get the full output
        response_text = ""
        if isinstance(output, list):
            # Join all chunks to get the complete response
            response_text = ''.join(output)
        else:
            # If output is not a list, convert to string
            response_text = str(output)
            
        print(f"\nRaw Response: {response_text}")
        
        # Check for HTML contribution marker
        html_contribution = None
        conversation_part = response_text
        
        # Use more lenient pattern matching - just look for "HTML CONTRIBUTION" anywhere
        import re
        html_contribution_match = re.search(r'(?i)[-_\s]*HTML\s*CONTRIBUTION[-_\s]*', response_text)
        if html_contribution_match:
            parts = re.split(r'(?i)[-_\s]*HTML\s*CONTRIBUTION[-_\s]*', response_text, 1)
            if len(parts) > 1:
                conversation_part = parts[0].strip()
                html_contribution = parts[1].strip()
                print(f"Found HTML contribution with lenient pattern: {html_contribution[:100]}...")
        
        reasoning_blocks = []
        for match in re.findall(r'<(think|thinking)>(.*?)</\1>', conversation_part, re.DOTALL | re.IGNORECASE):
            reasoning_blocks.append(match[1].strip())

        result = format_reasoning_response(conversation_part, reasoning_blocks)

        if html_contribution:
            result["html_contribution"] = html_contribution
            
        return result
        
    except Exception as e:
        print(f"Error calling DeepSeek via Replicate: {e}")
        print(f"Error type: {type(e)}")
        return None


def call_moonshot_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call Moonshot AI's official API."""
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        return "Error: MOONSHOT_API_KEY not found in environment variables"

    options = options or {}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for msg in conversation_history:
        content = msg.get("content")
        if not content:
            continue
        messages.append({"role": msg.get("role", "user"), "content": content})

    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
    }

    if "temperature" in options:
        payload["temperature"] = options["temperature"]
    if "max_tokens" in options:
        payload["max_tokens"] = options["max_tokens"]

    try:
        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return "No content in Moonshot response"

        message = choices[0].get("message", {})
        content = message.get("content", "") or ""
        return format_reasoning_response(content, [])
    except Exception as exc:
        print(f"Error calling Moonshot API: {exc}")
        return f"Error calling Moonshot API: {str(exc)}"


def call_bigmodel_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call BigModel (Zhipu) GLM models via official API."""
    api_key = os.getenv("BIGMODEL_API_KEY")
    if not api_key:
        return "Error: BIGMODEL_API_KEY not found in environment variables"

    options = options or {}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for msg in conversation_history:
        content = msg.get("content")
        if not content:
            continue
        messages.append({"role": msg.get("role", "user"), "content": content})

    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    if "temperature" in options:
        payload["temperature"] = options["temperature"]
    if "max_tokens" in options:
        payload["max_tokens"] = options["max_tokens"]

    try:
        response = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return "No content in BigModel response"

        message = choices[0].get("message", {})
        content = message.get("content", "") or ""
        return format_reasoning_response(content, [])
    except Exception as exc:
        print(f"Error calling BigModel API: {exc}")
        return f"Error calling BigModel API: {str(exc)}"


def call_gemini_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call Gemini models via official Google GenAI SDK."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY (or GEMINI_API_KEY) not found in environment variables"

    if not GENAI_AVAILABLE:
        print("Warning: google-genai SDK not available, falling back to REST API")
        return _call_gemini_rest_api(prompt, conversation_history, model, system_prompt, options)

    options = options or {}

    try:
        # Initialize client with API key
        client = genai.Client(api_key=api_key)

        # Build conversation history
        contents = []
        if conversation_history:
            for msg in conversation_history:
                text = msg.get("content")
                if not text:
                    continue
                role = msg.get("role", "user")
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text}]
                })

        # Add current prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        # Build config
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt

        # Build generation config
        generation_config = {}
        if "temperature" in options:
            generation_config["temperature"] = options["temperature"]
        if "top_p" in options:
            generation_config["top_p"] = options["top_p"]
        if "max_output_tokens" in options:
            generation_config["max_output_tokens"] = options["max_output_tokens"]

        # Enable thinking mode for Gemini 2.5 models
        from config import ENABLE_EXTENDED_THINKING, THINKING_BUDGET_TOKENS
        if ENABLE_EXTENDED_THINKING and "gemini-2" in model.lower():
            generation_config["thinking_config"] = {
                "thinking_budget": THINKING_BUDGET_TOKENS
            }

        if generation_config:
            config["generation_config"] = generation_config

        # Generate content
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

        # Extract text and thinking from response
        thinking_blocks = []
        text_content = ""

        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            # Extract thoughts if available
            if hasattr(candidate, 'thoughts') and candidate.thoughts:
                thinking_blocks = [str(thought) for thought in candidate.thoughts]
            # Extract text content
            parts = candidate.content.parts
            text_content = "".join(part.text for part in parts if hasattr(part, 'text'))
        else:
            text_content = str(response)

        return format_reasoning_response(text_content, thinking_blocks)

    except Exception as exc:
        print(f"Error calling Gemini API with SDK: {exc}")
        return f"Error calling Gemini API: {str(exc)}"


def _call_gemini_rest_api(prompt, conversation_history, model, system_prompt, options=None):
    """Fallback: Call Gemini models via REST API (legacy)."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY (or GEMINI_API_KEY) not found in environment variables"

    options = options or {}
    contents = []
    if conversation_history:
        for msg in conversation_history:
            text = msg.get("content")
            if not text:
                continue
            role = msg.get("role", "user")
            gemini_role = "user" if role == "user" else "model"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": text}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    body = {
        "contents": contents
    }
    if system_prompt:
        body["system_instruction"] = {"parts": [{"text": system_prompt}]}

    if any(key in options for key in ("temperature", "top_p", "max_output_tokens")):
        generation_config = body.setdefault("generationConfig", {})
        if "temperature" in options:
            generation_config["temperature"] = options["temperature"]
        if "top_p" in options:
            generation_config["topP"] = options["top_p"]
        if "max_output_tokens" in options:
            generation_config["maxOutputTokens"] = options["max_output_tokens"]

    url = (
        f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
        f"?key={api_key}"
    )

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return "No content in Gemini response"

        parts = candidates[0].get("content", {}).get("parts", [])
        text_segments = [part.get("text", "") for part in parts if part.get("text")]
        content = "\n".join(text_segments).strip()
        return format_reasoning_response(content, [])
    except Exception as exc:
        print(f"Error calling Gemini REST API: {exc}")
        return f"Error calling Gemini API: {str(exc)}"


def call_bedrock_claude_api(prompt, conversation_history, model, system_prompt, options=None):
    """Call Anthropic models deployed on AWS Bedrock."""
    client = get_bedrock_client()
    if not client:
        return "Error: AWS Bedrock client is not configured"

    options = options or {}
    messages = []
    for msg in conversation_history:
        text = msg.get("content")
        if not text:
            continue
        role = msg.get("role", "user")
        bedrock_role = "assistant" if role == "assistant" else "user"
        messages.append({
            "role": bedrock_role,
            "content": [{"type": "text", "text": text}]
        })

    messages.append({
        "role": "user",
        "content": [{"type": "text", "text": prompt}]
    })

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": options.get("max_tokens", 4000),
        "temperature": options.get("temperature", 1),
    }
    if system_prompt:
        body["system"] = system_prompt

    try:
        response = client.invoke_model(
            modelId=model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body).encode("utf-8")
        )
        raw_body = response.get("body")
        if hasattr(raw_body, "read"):
            parsed_body = json.loads(raw_body.read())
        else:
            parsed_body = json.loads(raw_body)

        content_blocks = parsed_body.get("content", [])
        text_segments = [
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text" and block.get("text")
        ]
        content = "\n".join(text_segments).strip()
        return format_reasoning_response(content, [])

    except (BotoCoreError, ClientError, json.JSONDecodeError) as exc:
        print(f"Error calling AWS Bedrock for model {model}: {exc}")
        return f"Error calling AWS Bedrock: {str(exc)}"


def _anthropic_provider(payload):
    return call_claude_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _bedrock_provider(payload):
    return call_bedrock_claude_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _openai_provider(payload):
    return call_openai_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _deepseek_provider(payload):
    return call_deepseek_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _deepseek_replicate_provider(payload):
    return call_deepseek_via_replicate(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _moonshot_provider(payload):
    return call_moonshot_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _bigmodel_provider(payload):
    return call_bigmodel_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


def _gemini_provider(payload):
    return call_gemini_api(
        payload["prompt"],
        payload["context_messages"],
        payload["model_id"],
        payload["system_prompt"],
        payload.get("options")
    )


PROVIDER_REGISTRY = {
    "anthropic": {
        "handler": _anthropic_provider,
        "supports_reasoning": True
    },
    "bedrock": {
        "handler": _bedrock_provider,
        "supports_reasoning": True
    },
    "openai": {
        "handler": _openai_provider,
        "supports_reasoning": True
    },
    "deepseek": {
        "handler": _deepseek_provider,
        "supports_reasoning": True
    },
    "deepseek_legacy": {
        "handler": _deepseek_replicate_provider,
        "supports_reasoning": True
    },
    "moonshot": {
        "handler": _moonshot_provider,
        "supports_reasoning": False
    },
    "bigmodel": {
        "handler": _bigmodel_provider,
        "supports_reasoning": False
    },
    "gemini": {
        "handler": _gemini_provider,
        "supports_reasoning": True
    }
}


def invoke_provider(provider_name, payload):
    """Invoke the appropriate provider based on configuration."""
    provider_key = provider_name.lower() if provider_name else None
    attempted = payload.setdefault("attempted_providers", [])
    if provider_key and provider_key not in attempted:
        attempted.append(provider_key)
    handler_entry = PROVIDER_REGISTRY.get(provider_key) if provider_key else None

    if handler_entry:
        handler = handler_entry.get("handler")
        try:
            raw_result = handler(payload)
            normalized = normalize_response(raw_result)
            if provider_key:
                normalized.setdefault("provider", provider_key)

            fallback_key = payload.get("fallback_provider")
            if (
                fallback_key
                and normalized.get("role") == "system"
                and normalized.get("content", "").lower().startswith("error")
            ):
                fallback_key = fallback_key.lower()
                if fallback_key not in payload["attempted_providers"]:
                    fallback_payload = dict(payload)
                    fallback_payload["model_id"] = payload.get("fallback_model", payload["model_id"])
                    return invoke_provider(fallback_key, fallback_payload)

            return normalized
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Error while invoking provider '{provider_key}': {exc}")
            return build_error_response(f"Provider '{provider_key}' error: {exc}")

    if provider_key == "deepseek":
        legacy_handler = PROVIDER_REGISTRY.get("deepseek_legacy", {}).get("handler")
        if legacy_handler and "deepseek_legacy" not in payload["attempted_providers"]:
            payload["attempted_providers"].append("deepseek_legacy")
            try:
                raw_result = legacy_handler(payload)
                normalized = normalize_response(raw_result)
                normalized.setdefault("provider", "deepseek_legacy")
                return normalized
            except Exception as exc:
                print(f"DeepSeek legacy fallback failed: {exc}")
                return build_error_response(f"DeepSeek legacy fallback error: {exc}")

    # Default to OpenRouter for unknown providers or community models
    if "openrouter" not in payload["attempted_providers"]:
        payload["attempted_providers"].append("openrouter")
    raw_result = call_openrouter_api(
        payload["full_messages"],
        payload["model_id"],
        payload.get("options")
    )
    normalized = normalize_response(raw_result)
    normalized.setdefault("provider", "openrouter")
    return normalized


def setup_image_directory():
    """Create an 'images' directory in the project root if it doesn't exist"""
    image_dir = Path("images")
    image_dir.mkdir(exist_ok=True)
    return image_dir

def cleanup_old_images(image_dir, max_age_hours=24):
    """Remove images older than max_age_hours"""
    current_time = datetime.now()
    for image_file in image_dir.glob("*.jpg"):
        file_age = datetime.fromtimestamp(image_file.stat().st_mtime)
        if (current_time - file_age).total_seconds() > max_age_hours * 3600:
            image_file.unlink()

def load_ai_memory(ai_number):
    """Load AI conversation memory from JSON files"""
    try:
        memory_path = f"memory/ai{ai_number}/conversations.json"
        with open(memory_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
            # Ensure we're working with the array part
            if isinstance(conversations, dict) and "memories" in conversations:
                conversations = conversations["memories"]
        return conversations
    except Exception as e:
        print(f"Error loading AI{ai_number} memory: {e}")
        return []

def create_memory_prompt(conversations):
    """Convert memory JSON into conversation examples"""
    if not conversations:
        return ""
    
    prompt = "Previous conversations that demonstrate your personality:\n\n"
    
    # Add example conversations
    for convo in conversations:
        prompt += f"Human: {convo['human']}\n"
        prompt += f"Assistant: {convo['assistant']}\n\n"
    
    prompt += "Maintain this conversation style in your responses."
    return prompt 


def print_conversation_state(conversation):
    print("Current conversation state:")
    for message in conversation:
        print(f"{message['role']}: {message['content'][:50]}...")  # Print first 50 characters of each message

def call_claude_vision_api(image_url):
    """Have Claude analyze the generated image"""
    try:
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail. What works well and what could be improved?"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url
                        }
                    }
                ]
            }]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error in vision analysis: {e}")
        return None

def list_together_models():
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.together.xyz/v1/models",
            headers=headers
        )
        
        print("\nAvailable Together AI Models:")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(json.dumps(models, indent=2))
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error listing models: {str(e)}")

def start_together_model(model_id):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # URL encode the model ID
        encoded_model = requests.utils.quote(model_id, safe='')
        start_url = f"https://api.together.xyz/v1/models/{encoded_model}/start"
        
        print(f"\nAttempting to start model: {model_id}")
        print(f"Using URL: {start_url}")
        response = requests.post(
            start_url,
            headers=headers
        )
        
        print(f"Start request status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("Model start request successful")
            return True
        else:
            print("Failed to start model")
            return False
            
    except Exception as e:
        print(f"Error starting model: {str(e)}")
        return False

def call_together_api(prompt, conversation_history, model, system_prompt):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Format messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.9,
            "top_p": 0.95,
        }
        
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        else:
            print(f"Together API Error Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error calling Together API: {str(e)}")
        return None

def read_shared_html(*args, **kwargs):
    return ""

def update_shared_html(*args, **kwargs):
    return False

def open_html_in_browser(file_path="conversation_full.html"):
    import webbrowser, os
    full_path = os.path.abspath(file_path)
    webbrowser.open('file://' + full_path)

def create_initial_living_document(*args, **kwargs):
    return ""

def read_living_document(*args, **kwargs):
    return ""

def process_living_document_edits(result, model_name):
    return result

def generate_image_from_text(text, model="gpt-image-1"):
    """Generate an image based on text using OpenAI's image generation API"""
    try:
        if not openai_client:
            return {
                "success": False,
                "error": "OPENAI_API_KEY not configured; cannot generate images."
            }
        
        # Create a directory for the images if it doesn't exist
        image_dir = Path("images")
        image_dir.mkdir(exist_ok=True)
        
        # Create a timestamp for the image filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate the image
        result = openai_client.images.generate(
            model=model,
            prompt=text,
            n=1,  # Generate 1 image
        )
        
        # Get the base64 encoded image
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        
        # Save the image to a file
        image_path = image_dir / f"generated_{timestamp}.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        
        print(f"Generated image saved to {image_path}")
        
        return {
            "success": True,
            "image_path": str(image_path),
            "timestamp": timestamp
        }
    except Exception as e:
        print(f"Error generating image: {e}")
        return {
            "success": False,
            "error": str(e)
        }
