# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a private AI career coach application built with the OpenAI Agents SDK. It provides personalized career guidance by leveraging professional documents (resume, LinkedIn profile, etc.) stored in `data/me/` to give contextually aware coaching advice.

## Architecture

### Core Components
- **app.py**: Main Gradio interface and CareerCoach agent creation with nest_asyncio fix
- **tools.py**: Document loading utilities and context retrieval functions
- **promptkit.py**: Simple template rendering system for prompts
- **prompts/coach_system.md**: System prompt template for the CareerCoach agent

### Key Design Patterns
- **Document Context Loading**: All professional documents from `data/me/` are loaded into the agent's system prompt context at creation time (no runtime tool calls needed)
- **Agent Pattern**: Uses OpenAI Agents SDK with `Agent`, `Runner`, and `function_tool` imports
- **Template Rendering**: Uses promptkit.py for variable substitution in prompt templates with `{variable}` syntax

### Data Flow
1. Agent creation loads all documents from `data/me/` into system prompt context
2. User queries are handled by the CareerCoach agent via Gradio interface
3. Agent has complete professional context available without needing to call retrieval tools during conversation

## Development Commands

### Running the Application
```bash
python app.py
```
The app launches on `127.0.0.1:7861` with a Gradio chat interface.

### Testing Tools
```bash
python tools.py
```
Tests the document retrieval and search functionality.

## Key Technical Details

### nest_asyncio Fix
The application uses `nest_asyncio.apply()` to handle nested event loops required by the OpenAI Agents SDK in Gradio environments.

### Document Processing
- PDF files processed with PyPDF2
- Text files read with UTF-8 encoding
- All documents concatenated into single context string for agent

### Environment Variables
Requires OpenAI API key in `.env` file (referenced in app.py via `load_dotenv()`).

## Professional Data Location

Personal documents are stored in `data/me/`:
- `resume.pdf`: Professional resume
- `linkedin.pdf`: LinkedIn profile export
- `summary.txt`: Professional summary text

These files are automatically loaded and made available to the CareerCoach agent's context.