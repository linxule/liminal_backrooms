# Neural Link Interface

A Python-based application that enables conversations between multiple AI models in a graphical user interface. The system supports various AI models including Claude, DeepSeek, OpenRouter models (GPT-4, Grok, Qwen), and Flux, allowing them to interact with each other through text and image generation.

## Features

- Multi-model AI conversations with support for:
  - Claude (Anthropic)
  - DeepSeek R1 (DeepSeek AI)
  - OpenRouter Models:
    - Gemini (Google)
    - Qwen (Alibaba)
    - LLaMA (Meta)
  - Flux (Black Forest Labs) for image generation
- Chain of Thought reasoning display for DeepSeek models
- Customizable conversation turns and modes (AI-AI or Human-AI)
- Multiple preset system prompt pairs
- Image generation and analysis capabilities
- Export functionality for conversations and generated images


## Prerequisites

- Python 3.10 or higher (but lower than 3.12)
- Poetry for dependency management
- Windows 10/11 or Linux (tested on Ubuntu 20.04+)

## API Keys Required

You'll need API keys from the following services to use all features:

1. Anthropic (Claude):
   - Sign up at: https://console.anthropic.com/
   - Endpoint: https://api.anthropic.com/v1/messages
   - Models: claude-3-opus, claude-3.5-sonnet, claude-3.5-haiku

2. OpenRouter:
   - Sign up at: https://openrouter.ai/
   - Endpoint: https://openrouter.ai/api/v1/chat/completions
   - Provides access to: GPT-4, Grok, Qwen, LLaMA, DeepSeek, and more

3. Replicate (for Flux):
   - Sign up at: https://replicate.com/
   - Used for image generation with Flux model

4. DeepSeek
   - current endpoint is at deepseek.com
   - now offered by others such as OpenRouter but it's not set up for this yet

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
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   REPLICATE_API_TOKEN=your_replicate_token
   OPENAI_API_KEY=your_openai_api_key  # Optional, for direct OpenAI access
   ```

2. Application Configuration (`config.py`):
   - Runtime settings (e.g., turn delay)
   - Available AI models in `AI_MODELS` dictionary
   - System prompt pairs in `SYSTEM_PROMPT_PAIRS` dictionary
   - Add new models or prompt pairs by updating these dictionaries

3. Memory System:
   - Create JSON files in `memory/ai-1` and `memory/ai-2` for conversation memory
   - Format: `{"memories": [{"human": "prompt", "assistant": "response"}]}`

4. Runtime Settings (via GUI):
   - Number of conversation turns: 2-10
   - Chat mode: AI-AI or Human-AI
   - Model selection for each AI
   - Prompt style selection

## Usage

1. Start the application:
```bash
poetry run python main.py
```

2. GUI Controls:
   - Mode Selection: Choose between AI-AI conversation or Human-AI interaction
   - Iterations: Set number of conversation turns (2-10)
   - AI Model Selection: Choose models for AI-1 and AI-2
   - Prompt Style: Select from predefined conversation styles
   - Input Field: Enter your message or initial prompt
   - Export: Save conversation and generated images

3. Special Features:
   - Chain of Thought: DeepSeek models show reasoning process
   - Image Generation: Flux model creates images from prompts
   - Export: Saves conversations and images with timestamps


## Troubleshooting

1. API Issues:
   - Check API key validity
   - Verify endpoint URLs in config
   - Check API rate limits
   - Monitor API response errors in console

2. GUI Issues:
   - Ensure tkinter is properly installed
   - Check Python version compatibility
   - Verify display resolution settings

3. Memory System:
   - Ensure memory directories exist
   - Check JSON file formatting
   - Monitor file permissions

4. Flux Image Generation:
   - Errors, assuming above is all good, are almost always nsfw refusals. Even fairly tame Sonnet prompts can trigger this.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - a permissive open-source license that allows you to:
- Use the software commercially
- Modify the source code
- Distribute the software
- Use it privately
- Sublicense it

The only requirement is that you include the original copyright notice and license terms in any copy of the software/source code.

Full license text can be found in the LICENSE file.

## Acknowledgments

- Anthropic's Claude API
- DeepSeek AI
- OpenRouter
- Black Forest Labs' Flux
- Open-source contributors

## Support

For issues and feature requests, please use the GitHub issue tracker.

