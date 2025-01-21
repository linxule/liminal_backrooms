# main.py

import time
import threading
import json
from config import (
    TURN_DELAY,
    AI_MODELS,
    SYSTEM_PROMPT_PAIRS
)
from shared_utils import (
    call_claude_api,
    call_openrouter_api,
    call_openai_api,
    call_replicate_api,
    call_deepseek_api
)
from gui import AIGUI, create_gui, run_gui

def is_image_message(message: dict) -> bool:
    """Returns True if 'message' contains a base64 image in its 'content' list."""
    if not isinstance(message, dict):
        return False
    content = message.get('content', [])
    if isinstance(content, list):
        for part in content:
            if part.get('type') == 'image':
                return True
    return False

def ai_turn(ai_name, conversation, model, system_prompt, gui=None):
    print(f"\n{'='*50}")
    print(f"Starting {model} turn...")
    print(f"Current conversation length: {len(conversation)}")
    
    # Determine if this is an image model conversation
    is_image_conversation = "flux" in AI_MODELS.get(model, "").lower() or any(
        "flux" in AI_MODELS.get(msg.get("model", ""), "").lower() 
        for msg in conversation 
        if isinstance(msg, dict)
    )
    
    # Load relevant memory file based on AI name
    memory_file = f"memory/{ai_name.lower()}/conversations.json"
    try:
        with open(memory_file, 'r') as f:
            memories = json.load(f)['memories']
            print(f"\nLoaded {len(memories)} memories for {ai_name}")
    except Exception as e:
        print(f"Error loading memories for {ai_name}: {e}")
        memories = []

    # Handle prompt selection based on conversation type and turn
    if is_image_conversation:
        if ai_name == "AI-1" and len(conversation) > 0:
            last_message = conversation[-1]
            if isinstance(last_message, dict) and "image_url" in last_message:
                prompt = f"The image model generated an image based on the prompt: {last_message.get('prompt', 'unknown prompt')}. Please continue the conversation by providing another detailed image generation prompt."
            else:
                prompt = last_message.get('content', 'Continue the conversation.') if isinstance(last_message, dict) else str(last_message)
        else:
            # Standard prompt handling for AI-2 (Flux) or other cases
            last_message = conversation[-1] if len(conversation) > 0 else None
            prompt = last_message.get('content', 'Continue the conversation.') if isinstance(last_message, dict) else str(last_message or "Start the conversation.")
    else:
        # Original prompt handling for non-image conversations
        if len(conversation) > 0:
            last_message = conversation[-1]
            prompt = last_message.get('content', 'Continue the conversation.') if isinstance(last_message, dict) else str(last_message)
        else:
            prompt = "Start the conversation."

    # Transform conversation history based on which AI is taking its turn
    full_context = []

    # Add memories first
    full_context.extend(memories)

    # Add all messages except the last one (which will be the prompt)
    for msg in conversation[:-1]:
        if not isinstance(msg, dict):
            full_context.append({
                "role": "user",
                "content": str(msg)
            })
            continue
            
        # For both AIs: their own messages are assistant, other AI's messages are user
        if msg.get("model") == model:
            full_context.append({
                "role": "assistant",
                "content": msg.get("display", msg.get("content", ""))
            })
        else:
            full_context.append({
                "role": "user",
                "content": msg.get("content", "")
            })

    # Print the processed conversation history for debugging
    print("\nProcessed conversation history:")
    for msg in full_context:
        print(f"Role: {msg['role']} | Content: {msg['content'][:100]}...")
    
    # Get the actual model ID from the display name
    model_id = AI_MODELS.get(model, model)
    
    # Make API calls based on model type
    if "claude" in model_id.lower():
        print("\n--- Prompt to Claude ---")
        print("System prompt:", system_prompt)
        print("Current user prompt:", prompt)
        print("Full context messages:")
        for msg in full_context:
            print("•", msg.get("role"), "|", msg.get("content", ""))
        print("------------------------")
        response = call_claude_api(prompt, full_context, model_id, system_prompt)
    elif "flux" in model_id.lower():
        response = call_replicate_api(prompt, [], model_id, gui)
    elif "gemini" in model_id.lower():
        response = call_openrouter_api(prompt, full_context, model_id, system_prompt)
    elif "o1" in model_id.lower():
        response = call_openai_api(prompt, full_context, model_id, system_prompt)
    elif "grok" in model_id.lower():
        response = call_openrouter_api(prompt, full_context, model_id, system_prompt)
    elif "qwen" in model_id.lower():
        response = call_openrouter_api(prompt, full_context, model_id, system_prompt)
    elif "deepseek" in model_id.lower():
        response = call_deepseek_api(prompt, full_context, model_id, system_prompt)
    elif "llama" in model_id.lower():
        response = call_openrouter_api(prompt, full_context, model_id, system_prompt)
    
    # Handle the response
    if response:
        print(f"\nRaw {model} Response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        if isinstance(response, dict):
            if "display" in response and "content" in response:
                # Handle DeepSeek response with Chain of Thought
                gui.append_text(f"\n{ai_name} ({model}):\n\n{response['display']}\n")
                conversation.append({
                    "role": "assistant",
                    "model": model,
                    "content": response["content"],
                    "display": response["display"],
                    "raw_content": json.dumps({
                        "role": "assistant",
                        "content": response["content"],
                        "chain_of_thought": response.get("display", "").split("[Final Answer]")[0].strip()
                    }, indent=2)
                })
            else:
                # Handle image generation response
                gui.append_text(f"\n{ai_name} ({model}): Generated an image based on the prompt\n")
                response.update({
                    "role": "assistant",
                    "model": model,
                    "content": response.get("content", "Flux model generated an image.")
                })
                conversation.append(response)

                if model == "Flux 1.1 Pro" and is_image_message(response):
                    # Now remove older image messages so we only have ONE in the entire history
                    for i in range(len(conversation) - 2, -1, -1):  # go backwards, skip the last appended message
                        if is_image_message(conversation[i]):
                            conversation[i]["content"] = [
                                {
                                    "type": "text",
                                    "text": "[prior image omitted to reduce token usage]"
                                }
                            ]
        else:
            gui.append_text(f"\n{ai_name} ({model}):\n\n{response}\n")
            conversation.append({
                "role": "assistant",
                "model": model,
                "content": response,
                "raw_content": json.dumps({
                    "role": "assistant",
                    "content": response
                }, indent=2)
            })
    else:
        print(f"\n{model} failed to respond")
        gui.append_text(f"\n{ai_name} ({model}): Failed to respond\n")
    
    print(f"Conversation length after {model} turn: {len(conversation)}")
    return conversation

def run_conversation(gui):
    print("Initializing conversation...")
    gui.conversation = []
    gui.turn_count = 0
    
    def process_turns(user_input=None):
        def run_conversation_thread():
            try:
                # Use passed input or get from field
                input_text = user_input if user_input else gui.input_field.get()
                if not input_text.strip():
                    gui.stop_loading()
                    return
                
                print(f"Processing input: {input_text}")
                
                # Get selected number of turns from dropdown
                max_turns = int(gui.turns_var.get())
                
                # Get selected models and prompt pair from GUI
                ai_1_model = gui.ai_1_model_var.get()
                ai_2_model = gui.ai_2_model_var.get()
                selected_prompt_pair = gui.prompt_pair_var.get()
                ai_1_prompt = SYSTEM_PROMPT_PAIRS[selected_prompt_pair]["AI_1"]
                ai_2_prompt = SYSTEM_PROMPT_PAIRS[selected_prompt_pair]["AI_2"]
                
                # Check if we've reached the maximum number of turns
                if gui.turn_count >= max_turns:
                    gui.append_text("\nMaximum number of turns reached. Starting new conversation.\n")
                    gui.conversation = []
                    gui.turn_count = 0
                
                # Check chat mode
                chat_mode = gui.mode_var.get()
                
                if chat_mode == "Human-AI":
                    # Always display the user's input
                    gui.append_text(f"\nYou: {input_text}\n")
                    gui.conversation.append({"role": "user", "content": input_text})
                    
                    # Update status
                    gui.status_bar.config(text=f"AI is thinking...")
                    
                    # Process AI-2's response
                    gui.conversation = ai_turn("AI-2", gui.conversation, ai_2_model, ai_2_prompt, gui)
                    gui.turn_count += 1
                else:
                    # For first turn in AI-AI mode, use user input
                    if gui.turn_count == 0:
                        gui.conversation.append({"role": "user", "content": input_text})
                        gui.append_text(f"\nYou: {input_text}\n")
                    
                    # Process both AIs' turns
                    while gui.turn_count < max_turns:
                        # Update status for AI-1
                        gui.status_bar.config(text=f"AI-1 is thinking...")
                        gui.conversation = ai_turn("AI-1", gui.conversation, ai_1_model, ai_1_prompt, gui)
                        time.sleep(TURN_DELAY)
                        
                        # Update status for AI-2
                        gui.status_bar.config(text=f"AI-2 is thinking...")
                        gui.conversation = ai_turn("AI-2", gui.conversation, ai_2_model, ai_2_prompt, gui)
                        time.sleep(TURN_DELAY)
                        
                        gui.turn_count += 1
                        print(f"Turn {gui.turn_count} completed")
                        
                        # Notify user about remaining turns
                        remaining_turns = max_turns - gui.turn_count
                        if remaining_turns > 0:
                            gui.append_text(f"\n({remaining_turns} turns remaining)\n")
                
            except Exception as e:
                print(f"Error during turn processing: {e}")
                gui.append_text(f"\nError during processing: {str(e)}\n")
            finally:
                # Always stop loading
                gui.master.after(0, gui.stop_loading)
        
        # Start the conversation processing in a separate thread
        thread = threading.Thread(target=run_conversation_thread)
        thread.daemon = True  # Thread will close when main program closes
        thread.start()
    
    # Set up the input callback
    gui.input_callback = process_turns

if __name__ == "__main__":
    print("Creating GUI...")
    gui = create_gui()
    gui.append_text("Welcome! Enter your message to start the conversation.\n")
    
    print("Setting up conversation...")
    run_conversation(gui)
    
    print("Starting GUI main loop...")
    run_gui(gui)