"""Career Coach AI - Fixed version with nest_asyncio."""

import nest_asyncio
import logging
import gradio as gr

from agents import Agent, Runner
from promptkit import render
from models import StructuredResponse
from config import load_config, get_config

# Apply nest_asycncio to allow nested event loops - THIS IS THE KEY FIX!
nest_asyncio.apply()

# Load configuration
config = load_config()

# Configure logging based on config
logging.basicConfig(
    level=getattr(logging, config.logging.level.upper()),
    format=config.logging.format
)

if config.logging.disable_httpx_noise:
    logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def create_coach_agent():
    """Create the CareerCoach agent with system prompt."""
    from tools import load_pdf_file, load_text_file, search_jobs

    # Load ALL documents into the system prompt context
    data_dir = config.user.data_directory

    # Ensure data directory exists
    if not data_dir.exists():
        logger.warning(f"Data directory does not exist: {data_dir}")
        full_context = "No user documents found."
    else:
        # Load all documents
        full_context = ""
        for file_path in data_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in config.documents.supported_extensions:
                try:
                    if file_path.suffix.lower() == ".pdf":
                        content = load_pdf_file(file_path)
                    elif file_path.suffix.lower() == ".txt":
                        content = load_text_file(file_path)
                    else:
                        continue

                    if content.strip():
                        full_context += f"\n\n=== {file_path.name.upper()} ===\n{content}\n"
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {e}")

    # Load and render system prompt with FULL context
    system_prompt = render(config.agent.instructions_template, {
        "name": config.user.name,
        "current_date": config.user.current_date
    })

    # Add full document context to system prompt
    system_prompt += f"\n\n## YOUR COMPLETE PROFESSIONAL CONTEXT:\n{full_context}"

    # Create agent WITH job search tool and structured output
    coach = Agent(
        name=config.agent.name,
        instructions=system_prompt,
        model=config.agent.model,
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
        height=config.interface.chatbot_height,
        type="messages",
        layout="bubble",
        show_copy_button=config.interface.show_copy_button,
        show_copy_all_button=config.interface.show_copy_all_button
    )

    demo = gr.ChatInterface(
        fn=chat_with_coach,
        type="messages",
        chatbot=custom_chatbot,
        title=config.interface.title,
        description=config.get_full_description(),
        examples=config.interface.examples
    )

    logger.info("🚀 Interface created, launching...")
    demo.launch(
        server_name=config.interface.server_name,
        server_port=config.interface.server_port,
        share=config.interface.share,
        show_error=config.interface.show_error
    )
