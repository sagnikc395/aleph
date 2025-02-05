# connect to anthropic

import os
from groq import Groq



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

print(Connection().chat_completion.choices[0].message.content)
