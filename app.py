"""Career Coach AI - Fixed version with nest_asyncio."""

import nest_asyncio
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

from agents import Agent, Runner
from promptkit import render

# Apply nest_asyncio to allow nested event loops - THIS IS THE KEY FIX!
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Configuration
NAME = "Amir"
CURRENT_DATE = datetime.now().strftime("%B %d, %Y")

def create_coach_agent():
    """Create the CareerCoach agent with system prompt."""

    # Load ALL documents into the system prompt context
    from tools import load_pdf_file, load_text_file
    from pathlib import Path

    current_dir = Path(__file__).parent
    data_dir = current_dir / "data" / "me"

    # Load all documents
    full_context = ""
    for file_path in data_dir.glob("*"):
        if file_path.is_file():
            if file_path.suffix.lower() == ".pdf":
                content = load_pdf_file(file_path)
            elif file_path.suffix.lower() == ".txt":
                content = load_text_file(file_path)
            else:
                continue

            if content.strip():
                full_context += f"\n\n=== {file_path.name.upper()} ===\n{content}\n"

    # Load and render system prompt with FULL context
    system_prompt = render("prompts/coach_system.md", {
        "name": NAME,
        "current_date": CURRENT_DATE
    })

    # Add full document context to system prompt
    system_prompt += f"\n\n## YOUR COMPLETE PROFESSIONAL CONTEXT:\n{full_context}"

    # Create agent WITHOUT tools - it has everything in context
    coach = Agent(
        name="CareerCoach",
        instructions=system_prompt,
        model="gpt-4o-mini"  # Using faster model for testing
    )

    return coach

def chat_with_coach(message, history):
    """Handle chat interactions with the career coach."""
    try:
        coach = create_coach_agent()
        # Now we can use run_sync directly
        result = Runner.run_sync(coach, message)
        return result.final_output

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Chat error: {error_msg}")
        return f"I apologize, but I encountered an error: {error_msg}"

if __name__ == "__main__":
    print("🚀 Creating Career Coach interface with nest_asyncio fix...")

    # Create interface with examples
    demo = gr.ChatInterface(
        fn=chat_with_coach,
        title="Career Coach AI - Phase 1",
        description=f"""
        Your private AI career coach, ready to help with career strategy, interview prep,
        resume reviews, and professional development.

        **Today is {CURRENT_DATE}**
        """,
        examples=[
            "What robotics experience do I have?",
            "Help me review my resume summary - I think it's too verbose",
            "What skills should I emphasize when applying for senior robotics roles?",
            "I'm considering a transition into AI/ML. What's the best path given my background?"
        ]
    )

    print("✅ Interface created, launching...")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,  # Using different port
        share=False,
        show_error=True
    )
