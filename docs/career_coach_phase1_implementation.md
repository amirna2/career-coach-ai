# Career Coach AI - Phase 1 Implementation Plan

## Overview
Building a private AI career coach using OpenAI Agents SDK that knows it's talking directly to YOU (the professional), not representing you to others.

## Technology Stack
- **Framework**: OpenAI Agents SDK (`pip install openai-agents`)
- **Core imports**: `from agents import Agent, Runner, function_tool`
- **UI**: Gradio for chat interface
- **Data**: JSON files for initial storage
- **Templates**: Reuse promptkit.py from personal-ai

## Project Structure
```
career-coach-ai/
├── pyproject.toml          # UV project configuration
├── .env                    # API keys (copy from personal-ai)
├── requirements.txt        # Dependencies
├── app.py                  # Main Gradio app + CareerCoach agent
├── models.py               # Pydantic schemas for structured JSON
├── tools.py                # retrieve_context function_tool
├── promptkit.py            # Copy from personal-ai for template rendering
├── prompts/
│   └── coach_system.md     # System prompt for CareerCoach
└── data/
    └── me/                 # Professional documents
        ├── resume.pdf      # Copy from personal-ai/me/
        ├── linkedin.pdf    # Copy from personal-ai/me/
        └── summary.txt     # Copy from personal-ai/me/

```

## Phase 1 Core Components

### 1. CareerCoach Agent (app.py)
```python
from agents import Agent, Runner, function_tool
from tools import retrieve_context
from promptkit import render

# Create coach with personalized system prompt
coach = Agent(
    name="CareerCoach",
    instructions=render("prompts/coach_system.md", {
        "name": "Amir",  # Your name
        "current_date": datetime.now()
    }),
    tools=[retrieve_context]
)
```

### 2. Retrieve Context Tool (tools.py)
```python
@function_tool
def retrieve_context(query: str) -> str:
    """Retrieve relevant sections from resume/LinkedIn/summary"""
    # Load documents from data/me/
    # Simple text search initially (no embeddings yet)
    # Return chunks with source tags: [resume], [linkedin]
```

### 3. Pydantic Models (models.py)
```python
class CoachingResponse(BaseModel):
    message: str
    recommendations: List[str]
    sources: List[str]  # ["resume", "linkedin", "summary"]
    
class CoachingIntent(BaseModel):
    intent: Literal["coaching", "job_analysis", "company_research", "application_help"]
    confidence: float
```

### 4. System Prompt (prompts/coach_system.md)
```markdown
You are an expert career coach working directly with {name}.
You have access to their professional documents and history.
Current date: {current_date}

Key behaviors:
- Address the user directly as "you" (not third person)
- Provide strategic career guidance and coaching
- Cite sources when referencing their background: [resume], [linkedin]
- Be concise, actionable, and strategic
- Focus on career advancement and skill development
```

### 5. Gradio Interface (app.py)
```python
import gradio as gr

def chat_with_coach(message, history):
    result = Runner.run_sync(coach, message)
    return result.final_output

demo = gr.ChatInterface(
    fn=chat_with_coach,
    title="Career Coach AI",
    description="Your private AI career coach"
)
```

## Implementation Steps

### Step 1: Project Setup
1. Create `career-coach-ai/` directory
2. Initialize with UV: `uv init`
3. Create virtual environment: `uv venv`
4. Install dependencies:
   - `openai-agents`
   - `gradio`
   - `pydantic`
   - `python-dotenv`
   - `PyPDF2` (for PDF parsing)

### Step 2: Copy Resources
1. Copy `.env` from personal-ai
2. Copy `promptkit.py` from personal-ai
3. Copy documents to `data/me/`
4. Import job_match models as needed

### Step 3: Build Core Components
1. Implement retrieve_context tool
2. Create coach_system.md prompt
3. Set up CareerCoach agent
4. Build Gradio interface

### Step 4: Test & Iterate
Test scenarios:
- "Help me shorten my resume summary"
- "What skills should I emphasize for robotics roles?"
- "I'm preparing for an interview, what should I focus on?"
- "Review my experience and suggest improvements"

## Key Differences from personal-ai

| Aspect | personal-ai (External) | career-coach-ai (Internal) |
|--------|------------------------|---------------------------|
| Audience | Website visitors | You (the professional) |
| Purpose | Represent you | Coach you |
| Perspective | "Amir has..." | "You have..." |
| Tone | Informational | Advisory/Strategic |
| Privacy | Public-facing | Private tool |

## Future Phases (After Phase 1 Success)

### Phase 1.5: Evaluator Pattern
- Add evaluation loop with feedback
- Implement response quality checks

### Phase 2: Job Analysis
- JobAnalysisAgent for detailed job matching
- Reuse job_match.py models from personal-ai

### Phase 3: Application Support
- Resume tailoring suggestions
- Cover letter generation

### Phase 4: Company Research
- Web search integration
- Company intelligence gathering

## Success Criteria for Phase 1
✅ Gradio chat interface launches successfully
✅ Coach introduces itself knowing it's talking to YOU
✅ Can retrieve and reference your professional documents
✅ Provides personalized coaching responses
✅ Maintains coaching dialogue naturally
✅ Sources are cited appropriately

## Notes
- Start minimal, test early and often
- Use structured JSON for all agent communication
- Consider Handoffs mechanism for multi-agent coordination later
- Evaluator with feedback loop pattern for quality control
- Decision on tools vs agents: Direct tools for simple operations, agents for complex workflows