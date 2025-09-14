"""Career Coach AI - Fixed version with nest_asyncio."""

import nest_asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from openai import OpenAI
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

    # Create agent WITH job search tool
    coach = Agent(
        name="CareerCoach",
        instructions=system_prompt,
        model="gpt-4o",  # Using stronger model for better instruction following
        tools=[search_jobs]
    )

    return coach

def chat_with_coach(message, history):
    """Handle chat interactions with the career coach using structured output."""
    try:
        # Use direct OpenAI client with structured output instead of Agents SDK
        from pathlib import Path
        import os

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Load system prompt same way as agent
        current_dir = Path(__file__).parent
        data_dir = current_dir / "data" / "me"

        # Load all documents
        full_context = ""
        for file_path in data_dir.glob("*"):
            if file_path.is_file():
                if file_path.suffix.lower() == ".pdf":
                    from tools import load_pdf_file
                    content = load_pdf_file(file_path)
                elif file_path.suffix.lower() == ".txt":
                    from tools import load_text_file
                    content = load_text_file(file_path)
                else:
                    continue

                if content.strip():
                    full_context += f"\n\n=== {file_path.name.upper()} ===\n{content}\n"

        # Load and render system prompt
        system_prompt = render("prompts/coach_system.md", {
            "name": NAME,
            "current_date": CURRENT_DATE
        })
        system_prompt += f"\n\n## YOUR COMPLETE PROFESSIONAL CONTEXT:\n{full_context}"

        # Convert Gradio history to OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": "user", "content": h[0]})
            messages.append({"role": "assistant", "content": h[1]})
        messages.append({"role": "user", "content": message})

        # Create tool definition for search_jobs
        tools = [{
            "type": "function",
            "function": {
                "name": "search_jobs",
                "strict": True,
                "description": "Search for job postings using DDGS syntax",
                "parameters": {
                    "type": "object",
                    "strict": True,
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Job title to search for"
                        },
                        "keywords": {
                            "type": "string",
                            "description": "DDGS search keywords - MUST use quotes around work arrangements like 'remote', 'hybrid', 'onsite'"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results"
                        }
                    },
                    "required": ["title", "keywords", "limit"],
                    "additionalProperties": False
                }
            }
        }]

        # Get structured response with tool handling
        logger.info(f"👉 INITIATING REQUEST - User: {message[:50]}...")

        done = False
        while not done:
            response = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                response_format=StructuredResponse
            )

            finish_reason = response.choices[0].finish_reason
            logger.info(f"🟢 FINISH REASON: {finish_reason}")

            # Handle tool calls if needed
            if finish_reason == "tool_calls":
                message_obj = response.choices[0].message
                tool_calls = message_obj.tool_calls
                logger.info(f"⚙️ TOOL CALLS DETECTED: {len(tool_calls)} calls")

                # Add assistant message with tool calls
                messages.append(message_obj)

                # Execute all tool calls
                for tool_call in tool_calls:
                    logger.info(f"   👁️‍🗨️ Tool: {tool_call.function.name}")
                    logger.info(f"   👁️‍🗨️ Args: {tool_call.function.arguments}")

                    # Execute the tool
                    if tool_call.function.name == "search_jobs":
                        try:
                            import json
                            from tools import _search_jobs
                            args = json.loads(tool_call.function.arguments)
                            logger.info(f"  EXECUTING search_jobs with args: {args}")
                            result = _search_jobs(**args)
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "content": result,
                                "tool_call_id": tool_call.id
                            })
                            logger.info(f"🟢 TOOL RESULT ADDED: {result[:200]}...")
                        except Exception as tool_error:
                            logger.error(f"❌ Tool execution failed: {tool_error}")
                            # Add error result to messages
                            messages.append({
                                "role": "tool",
                                "content": f"Error executing search_jobs: {str(tool_error)}",
                                "tool_call_id": tool_call.id
                            })

                logger.info(f"𖦹 CONTINUING LOOP FOR FINAL RESPONSE...")

            else:
                done = True
                structured_reply = response.choices[0].message.parsed

                # CRITICAL LOGGING
                logger.info(f"🌟 FINAL STRUCTURED RESPONSE RECEIVED")
                logger.info(f"   💬 Response:   { structured_reply.response[:100]}...")
                logger.info(f"   🧠 Reasoning:  {structured_reply.reasoning}")
                logger.info(f"   ⚙️ Tools Used: {structured_reply.tools_used}")
                logger.info(f"   📚 Facts Used: {structured_reply.facts_used}")

                return structured_reply.response

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Chat error: {error_msg}")
        return f"I apologize, but I encountered an error: {error_msg}"

if __name__ == "__main__":
    print("🚀 Creating Career Coach interface with nest_asyncio fix...")

    # Create interface with examples
    # Create custom chatbot with copy functionality
    custom_chatbot = gr.Chatbot(
        height=650,
        layout="bubble",
        show_copy_button=True,
        show_copy_all_button=True
    )

    demo = gr.ChatInterface(
        fn=chat_with_coach,
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

    print("🟢 Interface created, launching...")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,  # Using different port
        share=False,
        show_error=True
    )
