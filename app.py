"""Career Coach AI - Fixed version with nest_asyncio."""

import nest_asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set httpx to WARNING only to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from agents import Agent, Runner
from promptkit import render
from models import StructuredResponse

# Apply nest_asycncio to allow nested event loops - THIS IS THE KEY FIX!
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Configuration
NAME = "Amir"
CURRENT_DATE = datetime.now().strftime("%B %d, %Y")

def create_coach_agent():
    """Create the CareerCoach agent with system prompt."""

    # Load ALL documents into the system prompt context
    from tools import load_pdf_file, load_text_file, search_jobs
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

    # Create agent WITH job search tool and structured output
    coach = Agent(
        name="CareerCoach",
        instructions=system_prompt,
        model="gpt-4o-mini",  # Back to gpt-4o-mini
        tools=[search_jobs],
        output_type=StructuredResponse  # THIS ENABLES STRUCTURED OUTPUT!
    )

    return coach

def chat_with_coach(message, history):
    """Handle chat interactions with the career coach using Agents SDK."""
    try:
        logger.info(f"👉 PROCESSING MESSAGE: {message}")

        # Create the coach agent
        coach = create_coach_agent()

        # Use Agents SDK - it handles everything automatically!
        result = Runner.run_sync(coach, message)

        # Get the structured response
        structured_reply = result.final_output

        # Log the structured response details
        logger.info(f"🎉 STRUCTURED RESPONSE RECEIVED")
        logger.info(f"   💬 Response: {structured_reply.response[:100]}...")
        logger.info(f"   🧠 Reasoning: {structured_reply.reasoning}")
        logger.info(f"   ⚙️  Tools Used: {structured_reply.tools_used}")
        logger.info(f"   🗒  Facts Used: {structured_reply.facts_used}")

        return structured_reply.response

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"❌ Chat error: {error_msg}")
        return f"I apologize, but I encountered an error: {error_msg}"

if __name__ == "__main__":
    logger.info("🆕 Creating Career Coach...")

    # Create interface with examples
    # Create custom chatbot with copy functionality
    custom_chatbot = gr.Chatbot(
        height=650,
        type="messages",
        layout="bubble",
        show_copy_button=True,
        show_copy_all_button=True
    )

    demo = gr.ChatInterface(
        fn=chat_with_coach,
        type="messages",
        chatbot=custom_chatbot,
        title="Career Coach AI - Phase 1",
        description=f"""
        Your private AI career coach, ready to help with career strategy, interview prep,
        resume reviews, and professional development.

        **Today is {CURRENT_DATE}**
        """,
        examples=[
            "Help me tailor my resume summary for robotics teleops roles.",
            "What skills should I emphasize when applying for senior embedded software roles?",
            "I'm considering a transition into Technical Product Management role. What's the best path given my background?"
        ]
    )

    logger.info("🚀 Interface created, launching...")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        show_error=True
    )
