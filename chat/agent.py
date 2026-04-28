from django.conf import settings
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from knowledge_base.rag import get_context_for_llm
from .utils import FlattenedGemini
import logging

logger = logging.getLogger(__name__)

ESCALATION_SENTINEL = '__ESCALATE_TO_HUMAN__'


def _make_llm(model_name: str, temperature: float = 0):
    return FlattenedGemini(
        model=model_name,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
        request_timeout=60.0
    )


def wants_human_agent(message: str) -> bool:
    """
    Fast Gemini call to classify whether the user wants a human.
    Works for any phrasing, language, or typo.
    Falls back to backup model on timeout/503.
    """
    prompt = (
        "You are an intent classifier. "
        "Reply with only YES or NO.\n\n"
        "Does the following message express a desire to talk to a human, "
        "agent, support team, or get a callback / be contacted by a person?\n\n"
        f"Message: {message}"
    )
    for model_name in [settings.GOOGLE_TEXT_MODEL, settings.GOOGLE_TEXT_MODEL_BACKUP]:
        try:
            result = _make_llm(model_name).invoke(prompt)
            return result.content.strip().upper().startswith('YES')
        except Exception as e:
            logger.warning(f"⚠️ Model {model_name} failed for intent classification: {e}. Trying next...")
    logger.error("❌ All models failed for intent classification.")
    return False


def get_order_status(order_id: str) -> str:
    """Tool: Check order status (example — replace with real logic)"""
    return f"Order {order_id} is currently out for delivery and will arrive within 2-3 days."


def escalate_to_human(reason: str) -> str:
    """Tool: Signal that a human agent is needed. Returns sentinel string."""
    logger.info(f"🚨 Escalation triggered: {reason}")
    return ESCALATION_SENTINEL


def query_knowledge_base_tool(question: str, website_id: str) -> str:
    """Tool: Query knowledge base (pgvector RAG)"""
    try:
        context = get_context_for_llm(website_id, question)
        return str(context)
    except Exception as e:
        logger.error(f"❌ Knowledge base query failed: {e}")
        return f"Error querying knowledge base: {str(e)}"


def build_agent(website_id: str, session_id: str):
    # Try primary model, fall back to backup on failure
    llm = None
    for model_name in [settings.GOOGLE_TEXT_MODEL, settings.GOOGLE_TEXT_MODEL_BACKUP]:
        try:
            candidate = _make_llm(model_name, temperature=0.3)
            # Quick smoke-test invoke to confirm the model is reachable
            candidate.invoke("ping")
            llm = candidate
            logger.info(f"✅ Using model: {model_name}")
            break
        except Exception as e:
            logger.warning(f"⚠️ Model {model_name} unavailable: {e}. Trying next...")

    if llm is None:
        raise RuntimeError("❌ All Gemini models are unavailable. Cannot build agent.")

    tools = [
        Tool(
            name='DirectResponse',
            func=lambda x: x,
            description=(
            'Use this to respond directly to the customer WITHOUT querying any database. '
            'Use for greetings, small talk, casual conversation, or when you already know the answer. '
            'Input should be your response message.'
            )
        ),
        Tool(
            name='KnowledgeBase',
            func=lambda q: query_knowledge_base_tool(q, website_id),
            description=(
                'Use this to answer questions about the company, '
                'products, services, FAQs, policies, or any '
                'information from uploaded documents. '
                'Input should be the user question.'
            )
        ),
        Tool(
            name='OrderStatus',
            func=get_order_status,
            description=(
                'Use this to check the status of a customer order. '
                'Input should be the order ID provided by the customer.'
            )
        ),
        Tool(
            name='EscalateToHuman',
            func=escalate_to_human,
            description=(
                'Use this when: the customer asks to speak to a human, '
                'contact support, talk to an agent, get a callback, '
                'wants to be called, is frustrated, or the query cannot '
                'be answered from available information. '
                'Input should be a brief reason for escalation.'
            )
        ),
    ]

    react_prompt = PromptTemplate.from_template("""
You are a helpful and friendly customer support assistant.
Always be polite, warm, and professional.

IMPORTANT RULES:
- If the customer sends a greeting (hi, hello, hey, how are you, good morning, etc.) — respond naturally and warmly WITHOUT using any tools. Just greet them back and ask how you can help.
- If the customer sends small talk or casual messages — respond conversationally WITHOUT using any tools.
- Only use KnowledgeBase when customer asks something specific about the company, products, or services.
- Use EscalateToHuman when the customer asks to talk to a human, agent, or is frustrated.
- If KnowledgeBase returns no results, answer from your general knowledge or politely say you don't have that info.

You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Chat History:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}
""")

    memory = ConversationBufferWindowMemory(
        k=10,
        memory_key='chat_history',
        return_messages=False
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=60,
        early_stopping_method="generate"
    )

    return agent_executor