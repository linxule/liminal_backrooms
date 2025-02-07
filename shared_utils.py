# shared_utils.py

import requests
import logging
import replicate
import openai
import time
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
import base64
from together import Together
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Anthropic client with API key
anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def call_claude_api(prompt, conversation_history, model, system_prompt):
    try:
        client = Anthropic(
            api_key=os.environ['ANTHROPIC_API_KEY']
        )
        
        formatted_messages = []
        
        # Convert conversation history to text-only messages
        for msg in conversation_history:
            # If the message contains a list of content (might include images)
            if isinstance(msg.get('content'), list):
                # Extract only the text content
                text_parts = []
                for item in msg['content']:
                    if item.get('type') == 'text':
                        text = item.get('text', '')
                        if isinstance(text, str):
                            text_parts.append(text)
                
                if text_parts:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": " ".join(text_parts)
                    })
                    
                    # If this was a Flux message, add context about the image
                    if msg.get('prompt'):
                        formatted_messages.append({
                            "role": msg["role"],
                            "content": f"(The image was generated based on this prompt: {msg['prompt']})"
                        })
            # Handle display field for Chain of Thought
            elif msg.get('display'):
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["display"]
                })
            # Regular text message
            elif isinstance(msg.get('content'), str):
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
        # Add the current prompt with the latest image
        try:
            # Find the most recent image from Flux responses
            image_path = None
            for msg in reversed(conversation_history):
                if isinstance(msg, dict) and msg.get('image_path'):
                    image_path = msg['image_path']
                    break
            
            if image_path and Path(image_path).exists():
                with open(image_path, "rb") as image_file:
                    # Read image bytes and encode properly
                    image_bytes = image_file.read()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Add the current prompt with image
                    formatted_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    })
            else:
                # If no image found, just add the prompt as text
                formatted_messages.append({
                    "role": "user",
                    "content": prompt
                })
        except Exception as img_error:
            print(f"Error processing image: {img_error}")
            formatted_messages.append({
                "role": "user",
                "content": prompt
            })

        print("\nSending to Claude:")
        # Create debug version of messages without base64 data
        debug_messages = formatted_messages.copy()
        for msg in debug_messages:
            if isinstance(msg.get('content'), list):
                for part in msg['content']:
                    if part.get('type') == 'image':
                        part['source']['data'] = '[BASE64_IMAGE_DATA]'
        print(f"Messages: {json.dumps(debug_messages, indent=2)}")

        # Make the API call
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=system_prompt,
            messages=formatted_messages
        )
        
        # Extract the text content from the response
        if response and hasattr(response, 'content'):
            return response.content[0].text if isinstance(response.content, list) else str(response.content)
        return None

    except Exception as e:
        print(f"Error calling Claude API: {e}")
        print(f"Messages structure: {json.dumps(debug_messages, indent=2)}")  # Debug print
        return None

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

def call_openai_api(prompt, conversation_history, model, system_prompt):
    try:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": prompt})
        
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            # Increase max_tokens and add n parameter
            max_tokens=4000,
            n=1,
            temperature=0.8,
            stream=True
        )
        
        collected_messages = []
        for chunk in response:
            if chunk.choices[0].delta.content is not None:  # Changed condition
                collected_messages.append(chunk.choices[0].delta.content)
                
        full_reply = ''.join(collected_messages)
        return full_reply
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def call_openrouter_api(prompt, conversation_history, model, system_prompt):
    """Call the OpenRouter API to access various LLM models."""
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
            "X-Title": "AI Conversation"  # Adding title for OpenRouter tracking
        }
        
        # Format messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        for msg in conversation_history:
            if msg["role"] != "system":  # Skip system prompts
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,  # Using the exact model name from config
            "messages": messages,
            "temperature": 1,
            "max_tokens": 4000,
            "stream": False
        }
        
        print(f"\nSending to OpenRouter:")
        print(f"Model: {model}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
            else:
                print(f"Unexpected response structure: {response_data}")
                return None
        else:
            print(f"OpenRouter API error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        return None

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

def call_deepseek_api(prompt, conversation_history, model, system_prompt):
    """Call the DeepSeek model through Replicate API."""
    try:
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
                "max_tokens": 4000,
                "temperature": 0.7
            }
        )
        
        # Collect the response
        response_text = ''.join(output)
        print(f"\nRaw Response: {response_text}")
        
        # Try to extract reasoning from <think> tags in content
        reasoning = None
        content = response_text
        
        if content:
            import re
            # Try both <think> and <thinking> tags
            think_match = re.search(r'<(think|thinking)>(.*?)</\1>', content, re.DOTALL | re.IGNORECASE)
            if think_match:
                reasoning = think_match.group(2).strip()
                # Remove the thinking section from the content
                content = re.sub(r'<(think|thinking)>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # Format the response with both CoT and final answer
        display_text = ""
        if reasoning:
            display_text += f"[Chain of Thought]\n{reasoning}\n\n"
        if content:
            display_text += f"[Final Answer]\n{content}"
            
        return {
            "display": display_text,
            "content": content
        }
        
    except Exception as e:
        print(f"Error calling DeepSeek via Replicate: {e}")
        print(f"Error type: {type(e)}")
        return None

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

