# liminal_backrooms

A Python-based application that enables dynamic, branching conversations between multiple AI models in a graphical user interface. Allows for forking and rabbitholing by selecting text and right clicking. The system supports various AI models including Claude, OpenAI, Gemini, Grok etc, allowing them to interact with each other through text and image generation.

Huge thanks to Andy Ayrey and Janus for their endless inspiration.

## Features

- Multi-model AI conversations with support for:
  - Official APIs:
    - Anthropic Claude (latest Sonnet/Opus releases)
    - Anthropic Sonnet 3.x via AWS Bedrock (retired + sunset models)
    - OpenAI Responses API (o3 family, GPT‑5 family)
    - DeepSeek Chat & Reasoner
    - Moonshot Kimi K2 (0905)
    - BigModel GLM‑4.6 (Zhipu)
    - Gemini 2.5 Pro variants via Google AI Studio
  - OpenRouter ecosystem (Grok, Qwen, LLaMA, Gemini, etc.)
  - OpenAI Images (gpt-image-1) for image generation (toggle in GUI)

- Dynamic Conversation Branching:
  - 🕳️ Rabbithole: Explore concepts in depth while retaining full context
  - 🔱 Fork: Continue conversations from specific points in new directions
  - Visual network graph showing conversation branches and connections
  - Drag-and-drop node organization
  - Automatic node spacing and collision avoidance
  - Easy navigation between branches
  - User can also interject at these points

- Advanced Features:
  - Chain of Thought reasoning display optional
  - Customizable conversation turns and modes (AI-AI or Human-AI)
  - Preset system prompt pairs
  - Image generation and analysis capabilities
  - Export functionality for conversations and generated images
  - Modern dark-themed GUI interface
  - Conversation memory system

## Prerequisites

- Python 3.10 or higher (but lower than 3.12)
- Poetry for dependency management
- Windows 10/11 or Linux (tested on Ubuntu 20.04+)

## API Keys Required

You'll need API keys from the following services to use all features (only configure what you plan to call):

- **Anthropic (direct API):** `ANTHROPIC_API_KEY`  
  Access the latest Claude Sonnet/Opus releases directly.
- **AWS Bedrock (Anthropic on AWS):** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`, and `AWS_REGION`  
  Required for retired or sunset Claude Sonnet models (Sonnet 3 / 3.5).
- **OpenAI Responses & Images:** `OPENAI_API_KEY`  
  Powers the Responses API (o3, GPT‑5 family) and image generation (`gpt-image-1`).
- **DeepSeek:** `DEEPSEEK_API_KEY`  
  Official chat and reasoning endpoints.
- **Moonshot AI (Kimi):** `MOONSHOT_API_KEY`  
  Official access to the Kimi K2 0905 model.
- **BigModel / Zhipu GLM:** `BIGMODEL_API_KEY`  
  Official GLM‑4.6 chat endpoint.
- **Google AI Studio (Gemini 2.5 Pro):** `GOOGLE_API_KEY` (alias `GEMINI_API_KEY`)  
  Official Gemini 2.5 Pro variants via Google AI Studio REST API.
- **OpenRouter (optional but recommended):** `OPENROUTER_API_KEY`  
  Provides access to Grok, Qwen, Meta LLaMA, Gemini previews, etc.
- **Replicate (optional):** `REPLICATE_API_TOKEN`  
  Required only for legacy DeepSeek R1 via Replicate or Flux image generation.

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Install Poetry if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies using Poetry:
```bash
poetry install
```

4. Create a `.env` file in the project root with your API keys (see Configuration section below)

## Configuration

1. Environment Variables (`.env`):
   - Create a `.env` file in the project root with your API keys:
   ```env
   # Direct provider APIs
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   MOONSHOT_API_KEY=your_moonshot_api_key
   BIGMODEL_API_KEY=your_bigmodel_api_key
   GOOGLE_API_KEY=your_google_ai_studio_key

   # AWS Bedrock (optional for Claude Sonnet 3.x/3.5 legacy access)
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_REGION=us-east-1

   # Aggregators / optional services
   OPENROUTER_API_KEY=your_openrouter_api_key
   REPLICATE_API_TOKEN=your_replicate_token
   ```
   - A template is available at `.env.example`; copy it with `cp .env.example .env` and fill in the values you intend to use for this project.
   - Optional: automate loading with tools like `direnv` or `dotenvx` so the project's `.env` is applied whenever you enter the repository.

2. Application Configuration (`config.py`):
   - Runtime settings (e.g., turn delay)
   - Available AI models in `AI_MODELS` dictionary
   - System prompt pairs in `SYSTEM_PROMPT_PAIRS` dictionary
   - Official integrations now include structured metadata (provider, capabilities, options); community/OpenRouter entries remain simple strings for backward compatibility
   - Add new models or prompt pairs by updating these dictionaries

3. Memory System (optional):
   - Place JSON files at `memories/ai-1_memories.json` and `memories/ai-2_memories.json`
   - Contents should be a JSON array of prior messages (simple strings are fine)

## Usage

1. Start the application:
```bash
poetry run python main.py
```

2. GUI Controls:
   - Mode Selection: Choose between AI-AI conversation or Human-AI interaction
   - Iterations: Set number of conversation turns (1-100)
   - AI Model Selection: Choose models for AI-1 and AI-2
   - Prompt Style: Select from predefined conversation styles
   - Input Field: Enter your message or initial prompt
   - Export: Save conversation and generated images

3. Branching Features:
   - Right-click on any text to access branching options:
     - 🕳️ Rabbithole: Explore a concept in depth
     - 🔱 Fork: Continue from a specific point
   - Click nodes in the network graph to navigate between branches
   - Adjust iterations and models on the fly without restarting the application
   - Drag nodes to organize your conversation map
   - Branches automatically space themselves for clarity
   - (Branching doesn't work very well with images in the GUI yet. The images disappear but will still be produced and can be found in the images folder.)

4. Special Features:
   - Chain of Thought: DeepSeek, OpenAI o-series, and other reasoning models surface thinking traces when `SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT` is enabled
   - Image Generation: OpenAI Images (gpt-image-1) creates images from prompts
   - Export: Saves conversations and images with timestamps

## Troubleshooting

1. API Issues:
   - Check API key validity
   - Verify endpoint URLs in config
   - Check API rate limits
   - Monitor API response errors in console

2. GUI Issues:
   - Ensure PyQt6 is installed (handled by Poetry install)
   - Check Python version compatibility
   - Verify display resolution settings

3. Memory System:
   - Ensure memory files exist in `memories/`
   - Check JSON formatting
   - Monitor file permissions

4. Branching Issues:
   - If nodes overlap, try dragging them apart
   - If a branch seems stuck, try clicking propagate again
   - Check console for any error messages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Anthropic
- DeepSeek AI
- OpenRouter
- OpenAI
- Open-source contributors
- Andy Ayrey and Janus, both huge inspirations for this project

## Support

For issues and feature requests, please use the GitHub issue tracker.
