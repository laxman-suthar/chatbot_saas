from django.conf import settings
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from knowledge_base.rag import query_knowledge_base
from .tasks import send_whatsapp_escalation
from .utils import FlattenedGemini


ESCALATION_SENTINEL = '__SHOW_CALLBACK_FORM__'


def wants_human_agent(message: str) -> bool:
    """
    Use a fast Gemini call to classify whether the user's intent
    is to reach a human — works for any phrasing, language, or typo.
    """
    llm = FlattenedGemini(
        model=settings.GOOGLE_TEXT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        convert_system_message_to_human=True,
    )
    prompt = (
        "You are an intent classifier. "
        "Reply with only YES or NO.\n\n"
        "Does the following message express a desire to talk to a human, "
        "agent, support team, or get a callback / be contacted by a person?\n\n"
        f"Message: {message}"
    )
    try:
        result = llm.invoke(prompt)
        return result.content.strip().upper().startswith('YES')
    except Exception:
        return False


def get_order_status(order_id: str) -> str:
    return f"Order {order_id} is currently out for delivery and will arrive within 2-3 days."


def escalate_to_human(reason: str) -> str:
    send_whatsapp_escalation.delay(reason)
    return ESCALATION_SENTINEL


def query_knowledge_base_tool(question: str, website_id: str) -> str:
    try:
        result = query_knowledge_base(website_id, question)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def build_agent(website_id: str, session_id: str):
    llm = FlattenedGemini(
        model=settings.GOOGLE_TEXT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.3,
        convert_system_message_to_human=True
    )

    tools = [
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
                'Also use this when the customer expresses any intent to '
                'connect with the team, staff, or a real person in any way. '
                'Input should be a brief reason for escalation.'
            )
        ),
    ]

    react_prompt = PromptTemplate.from_template("""
You are a helpful and friendly customer support assistant.
Always be polite and professional.
Use the available tools to answer customer queries accurately.
Answer questions directly from the document content.

IMPORTANT: Use the EscalateToHuman tool whenever the customer:
- Asks to talk/speak/chat with a human, agent, person, or team member
- Asks for a callback, to be called, or to contact support
- Expresses frustration or says their issue is urgent
- Uses phrases like "connect me", "transfer me", "I want help from a person", etc.
- You cannot find the answer after checking the KnowledgeBase
Do NOT just reply with text saying you've escalated — always use the EscalateToHuman tool.

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

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt
    )

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