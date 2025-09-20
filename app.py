"""Career Coach AI - Fixed version with nest_asyncio."""

import nest_asyncio
import logging
import gradio as gr
import os
import socket
import re

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

def _is_port_free(host: str, port: int) -> bool:
    """Return True if the port is available for binding on given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def _find_ephemeral_port(host: str) -> int:
    """Ask OS for an available ephemeral port and return it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]

def _pick_server_port(preferred_port: int, host: str) -> int:
    """Pick a server port respecting GRADIO_SERVER_PORT and availability."""
    env_port_value = os.getenv("GRADIO_SERVER_PORT")
    if env_port_value:
        try:
            env_port = int(env_port_value)
            if _is_port_free(host, env_port):
                logger.info(f"Using port from GRADIO_SERVER_PORT: {env_port}")
                return env_port
            else:
                logger.warning(f"Port {env_port} from GRADIO_SERVER_PORT is busy. Selecting a free port.")
        except ValueError:
            logger.warning(f"Invalid GRADIO_SERVER_PORT value: {env_port_value}. Falling back to config or free port.")

    if preferred_port and _is_port_free(host, preferred_port):
        return preferred_port

    free_port = _find_ephemeral_port(host)
    logger.info(f"Preferred port unavailable. Using free port: {free_port}")
    return free_port

def create_coach_agent():
    """Create the CareerCoach agent with system prompt."""
    from tools import load_pdf_file, load_text_file
    from tools.job_search import browser_search_jobs, build_jobs_search_query

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
        tools=[build_jobs_search_query, browser_search_jobs],
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


def _infer_job_search_params(user_message: str) -> tuple[str | None, str]:
    """Infer a plausible (title, expression) from a free-form user message."""
    text = user_message.strip()
    # Extract a likely title
    title_pattern = re.compile(r"\b(?:(Senior|Staff|Principal)\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(Engineer|Developer|Scientist|Manager|Architect|Researcher)\b")
    title_match = title_pattern.search(text)
    title: str | None = None
    if title_match:
        seniority = title_match.group(1) or ""
        base = title_match.group(2)
        role = title_match.group(3)
        title = " ".join([p for p in [seniority, base, role] if p])

    expression_parts: list[str] = []
    lowered = text.lower()
    if "remote" in lowered:
        expression_parts.append("remote")
    alt_terms: list[str] = []
    if "iot" in lowered:
        alt_terms.append("iot")
    if "robot" in lowered:
        alt_terms.append("robotics")
    if "ai" in lowered or "machine learning" in lowered:
        alt_terms.append("AI")
    if len(alt_terms) == 1:
        expression_parts.append(alt_terms[0])
    elif len(alt_terms) > 1:
        expression_parts.append("(" + " || ".join(alt_terms) + ")")
    exclusions: list[str] = []
    for term in ["react", "typescript", "front end", "frontend"]:
        if term in lowered:
            exclusions.append(term.replace(" ", ""))
    if exclusions:
        expression_parts.extend([f"-{ex}" for ex in exclusions])
    expression = " && ".join(expression_parts)
    return title, expression

if __name__ == "__main__":
    logger.info("🆕 Creating Career Coach...")

    def on_submit(message: str, history: list, plan_state: dict):
        """Handle user submission: get coach reply and update plan state."""
        response = chat_with_coach(message, history)
        title, expression = _infer_job_search_params(message)
        updated_plan = {
            "title": title or "Software Engineer",
            "expression": expression
        }
        # Maintain messages-typed history
        updated_history = (history or []) + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ]
        return "", updated_history, updated_plan

    def on_open_search(plan_state: dict, history: list):
        """Open ATS searches using the current plan state."""
        title = (plan_state or {}).get("title") or "Software Engineer"
        expression = (plan_state or {}).get("expression") or ""
        try:
            from tools.job_search import browser_search_jobs
            # The tool is decorated; call the underlying wrapped function for direct execution
            callable_fn = getattr(browser_search_jobs, "__wrapped__", None)
            if callable_fn is None:
                raise TypeError("browser_search_jobs FunctionTool is not directly callable and missing __wrapped__")
            result = callable_fn(title=title, expression=expression)
            logger.info(f"🌐 Opened ATS searches: {result[:200]}...")
            confirmation = f"Opening ATS searches for '{title}' with expression: {expression or '(none)'}"
        except Exception as e:
            confirmation = f"Failed to open ATS searches: {type(e).__name__}: {e}"
            logger.warning(confirmation)
        updated_history = (history or []) + [
            {"role": "assistant", "content": confirmation}
        ]
        return updated_history

    with gr.Blocks() as demo:
        gr.Markdown(f"# {config.interface.title}")
        gr.Markdown(config.get_full_description())

        chatbot = gr.Chatbot(
            height=config.interface.chatbot_height,
            type="messages",
            layout="bubble",
            show_copy_button=config.interface.show_copy_button,
            show_copy_all_button=config.interface.show_copy_all_button
        )

        with gr.Row():
            msg = gr.Textbox(placeholder="Type your message...", scale=4)
            send_btn = gr.Button("Send", variant="primary")
            open_btn = gr.Button("Open ATS searches", variant="secondary")

        plan_state = gr.State({"title": None, "expression": ""})

        msg.submit(on_submit, inputs=[msg, chatbot, plan_state], outputs=[msg, chatbot, plan_state])
        send_btn.click(on_submit, inputs=[msg, chatbot, plan_state], outputs=[msg, chatbot, plan_state])
        open_btn.click(on_open_search, inputs=[plan_state, chatbot], outputs=[chatbot])

    logger.info("🚀 Interface created, launching...")
    chosen_port = _pick_server_port(config.interface.server_port, config.interface.server_name)
    demo.launch(
        server_name=config.interface.server_name,
        server_port=chosen_port,
        share=config.interface.share,
        show_error=config.interface.show_error
    )
