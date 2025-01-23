# making a simple chatbot
#
#

import os
from groq import Groq
from atomic_agents.lib.components.agent_memory import AgentMemory
from rich.console import Console
from atomic_agents.agents.base_agent import BaseAgentOutputSchema,\
BaseAgent,BaseAgentConfig

class Connection:
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY")
    )

    chat_completion = client.chat.completions.create(
        messages=[{
            "role":"user",
            "content":"Explain the philosophy of Nietzsche",
        }],
        model="llama3-8b-8192"
    )

OPENAI_KEY = os.getenv("OPENAI_API")



console = Console()

memory = AgentMemory()


##init memory with initial message from the assistant
initial_message = BaseAgentOutputSchema(chat_message="project alpeh v0 > ")
memory.add_message("assistant",initial_message)

# OpenAI client setup using the Instructor library
client = instructor.from_openai(openai.OpenAI(api_key=API_KEY))


agent = BaseAgent(
    config=BaseAgentConfig(
        client=client,
        model="gpt-4o-mini",
        memory=memory,
    )
)
