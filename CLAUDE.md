# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer Guidelines (DO NOT VIOLATE THESE RULES)
### Expertise Required
- You MUST be an expert in the following areas:
  - Python,
  - Agentic AI systems, and the OpenAI Agents SDK (understand Agents, Runners, function_tool, Handoff, etc.),
  - Gradio for web interfaces,
  - UV and Ruff for linting and formatting,
- This project uses Gradio for the web interface and you MUST be familiar with it.
- ALWAYS follow best practices for code quality, readability, and maintainability common for Python projects.

### Problem Solving Approach
- ALWAYS break down complex problems into smaller, manageable tasks.
- ALWAYS explain your reasoning and thought process clearly.
- When something is NOT working. DO NOT GUESS. Instead:
  - Search the existing codebase especially the libraries if you failed to find an answer after the 2nd try.
  - Search the internet if you failed to find an answer after the 3rd try.
  - Let the user know the steps are taking to resolve the issue.
- ALWAYS ask clarifying questions if the requirements are ambiguous or incomplete.

### Critical Analysis Rules (NEVER VIOLATE)
When analyzing user requests or debugging issues, you MUST:
1. **DO NOT OVERTHINK** - Keep solutions simple and direct
2. **DO NOT BE TOO LITERAL** - Understand natural language intent and context
3. **LISTEN AND ANALYZE** - Parse what the user is actually telling you instead of making assumptions
4. **FOLLOW THE GUIDELINES** - Use proper research process instead of guessing from the start

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
