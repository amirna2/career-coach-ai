# Career Coach AI

A private AI career coach built with the OpenAI Agents SDK that provides personalized career guidance by leveraging your professional documents.

## Features

- **Personalized Coaching**: Analyzes your resume, LinkedIn profile, and professional summary to provide contextually relevant advice
- **Career Strategy**: Helps with career transitions, skill development, and professional growth planning
- **Interview Preparation**: Provides tailored interview prep based on your actual experience
- **Resume Optimization**: Reviews and suggests improvements to your resume content
- **Private & Secure**: All processing happens locally with your documents, only API calls to OpenAI for responses

## Setup

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Or if using UV:
   ```bash
   uv sync
   ```

3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Add your professional documents to the `data/me/` directory:
   - `resume.pdf` - Your current resume
   - `linkedin.pdf` - LinkedIn profile export (optional)
   - `summary.txt` - Professional summary or bio (optional)

## Running the Application

Start the career coach interface:

```bash
python app.py
```

The application will launch a web interface at `http://127.0.0.1:7861`

## Usage

Once running, you can interact with your AI career coach through the web interface. Example queries:

- "What robotics experience do I have?"
- "Help me review my resume summary - I think it's too verbose"
- "What skills should I emphasize when applying for senior robotics roles?"
- "I'm considering a transition into AI/ML. What's the best path given my background?"

## How It Works

The application loads all your professional documents into the AI agent's context at startup, allowing it to provide personalized advice based on your actual background and experience. The agent uses OpenAI's GPT models to analyze your documents and provide strategic career guidance.

## Project Structure

```
career-coach-ai/
├── app.py              # Main application and Gradio interface
├── tools.py            # Document loading and processing utilities
├── promptkit.py        # Template rendering for prompts
├── pyproject.toml      # Project dependencies and metadata
├── .env               # Environment variables (create this)
├── prompts/
│   └── coach_system.md # AI agent system prompt
└── data/
    └── me/            # Your professional documents go here
        ├── resume.pdf
        ├── linkedin.pdf (optional)
        └── summary.txt (optional)
```

## Privacy & Security

- Your documents are processed locally and only sent to OpenAI as part of the conversation context
- No data is stored or transmitted beyond what's necessary for the AI responses
- All processing happens on your local machine

## Dependencies

- `openai-agents` - OpenAI Agents SDK
- `gradio` - Web interface
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management
- `PyPDF2` - PDF document processing
- `nest-asyncio` - Async event loop handling

## Troubleshooting

If you encounter issues with nested event loops, the application includes a `nest_asyncio.apply()` fix that should resolve most async-related problems with Gradio and the OpenAI Agents SDK.