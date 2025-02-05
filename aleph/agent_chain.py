"""
Agent Chain for Chaining Protocols (Extract, Atomize, Reflect, Integrate)
with Per‑Protocol Reservoir Access and a Single Working Memory File (instance.md).

Directory structure expected:
  - patterns/             # Contains full protocol instruction Markdown files:
       Extract.md
       Atomize.md
       Reflect.md
       Integrate.md
  - reservoir/            # Contains reservoir files that provide guidance for each protocol, e.g.:
       Intuition_Reservoir.md
       Abstraction_Theory.md
       Abstraction_Theory_Picture.md
  - instance.md           # The working memory file (Markdown) that accumulates outputs

Each protocol instance is configured with:
  - A prompt file (from patterns/)
  - An "accesses" dictionary mapping descriptive labels (e.g., "Intuition Reservoir") to reservoir filenames (from reservoir/).
  - A boolean flag (include_in_chain) that controls whether that protocol is executed.
"""
# ------------------------------------------------------------------------------
# AgentChain: Extended Agent Using a Single Working Memory File (instance.md)
# ------------------------------------------------------------------------------
# Import base agent components; adjust the paths as needed.
from asyncio import Protocol
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from atomic_agents.agents.base_agent import (
    BaseAgent,
    BaseAgentConfig,
    BaseAgentInputSchema,
)
from openai import BaseModel

from aleph.main import obtain_commentary
from aleph.utils import load_markdown


class AgentChain(BaseAgent):
    """
    An agent that processes raw input through a chain of protocols.

    For each protocol, the full prompt is built by concatenating:
      1. The protocol's instruction text (from patterns/).
      2. The access contexts: for each entry in the protocol's accesses, the reservoir file content (from reservoir/).
      3. The raw user input.
      4. The current accumulated instance context (from instance.md).

    After executing a protocol, its output is appended to the instance file as a new section.
    """

    def __init__(self, config: BaseAgentConfig, instance_file: str = "instance.md"):
        super().__init__(config)
        self.instance_file = Path(instance_file)
        # Initialize the working memory file with a header.
        self.instance_file.write_text("# Internal Reservoir Instance\n\n")

    def _read_instance(self) -> str:
        return self.instance_file.read_text() if self.instance_file.exists() else ""

    def _write_instance(self, content: str):
        self.instance_file.write_text(content)

    def _append_to_instance(self, section_title: str, content: str):
        current = self._read_instance()
        section = f"\n\n---\n### {section_title}\n\n{content}\n"
        updated = current + section
        self._write_instance(updated)

    def get_response(
        self, response_model=None, user_input: Optional[BaseAgentInputSchema] = None
    ) -> Type[BaseModel]:
        """
        Extended get_response that invokes the LLM synchronously.
        Maximum tokens are set to 8096.
        """
        if response_model is None:
            response_model = self.output_schema

        if user_input:
            self.memory.initialize_turn()
            self.current_user_input = user_input
            self.memory.add_message("user", user_input)

        messages = [
            {
                "role": "system",
                "content": self.system_prompt_generator.generate_prompt(),
            },
        ] + self.memory.get_history()

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            response_model=response_model,
            temperature=self.temperature,
            max_tokens=8096,
        )
        self.memory.add_message("assistant", response)
        return response

    def run_protocol(
        self, user_input: str, protocol: Protocol, reservoir_dir: Path
    ) -> str:
        """
        Runs a single protocol synchronously...
        """
        if not protocol.include_in_chain:
            print(f"Skipping protocol '{protocol.name}' (flag set to False).")
            return ""

        commentary_text = ""
        if protocol.requires_commentary:
            commentary_text = obtain_commentary(protocol.name)
            # You can either append commentary_text into the user input (as before) or add
            # a separate section for commentary that appears before the input.

        instance_content = self._read_instance()
        # Build the access context by iterating through each reservoir (or working memory).
        access_context_parts = []
        for label, filename in protocol.accesses.items():
            if filename.strip().lower() == "instance.md":
                content = self._read_instance()
                access_context_parts.append(f"### {label} (Working Memory):\n{content}")
            else:
                try:
                    content = load_markdown(str(reservoir_dir / filename))
                    access_context_parts.append(f"### {label}:\n{content}")
                except Exception as e:
                    logging.warning(
                        f"Could not load reservoir '{label}' from file '{filename}': {e}"
                    )
        access_context = "\n\n".join(access_context_parts)

        # Build the full prompt; if commentary is provided, insert it as its own section before the user input.
        commentary_section = (
            f"\n\nCommentary for {protocol.name}:\n{commentary_text}"
            if commentary_text
            else ""
        )

        full_prompt = (
            f"Protocol: {protocol.name}\n"
            f"Instructions:\n{protocol.prompt}\n\n"
            f"Access Contexts:\n{access_context}\n"
            f"{commentary_section}\n\n"  # commentary inserted here into the context
            f"User Input:\n{user_input}\n\n"
            f"Current Instance Context:\n{instance_content}\n"
        )

        # Temporarily override the system prompt generator
        original_generate_prompt = self.system_prompt_generator.generate_prompt
        self.system_prompt_generator.generate_prompt = lambda: full_prompt

        agent_input = self.input_schema(chat_message=full_prompt)
        response = self.run(agent_input)
        result_text = response.chat_message.strip()

        # Restore the original prompt generation function
        self.system_prompt_generator.generate_prompt = original_generate_prompt
        self._append_to_instance(f"{protocol.name} Output", result_text)

        return result_text

    async def run_protocol_async(
        self, user_input: str, protocol: Protocol, reservoir_dir: Path
    ) -> str:
        """
        Asynchronous variant of run_protocol.
        """
        if not protocol.include_in_chain:
            print(f"Skipping protocol '{protocol.name}' (flag set to False).")
            return ""

        instance_content = self._read_instance()
        # Build access_context similarly for async execution.
        access_context_parts = []
        for label, filename in protocol.accesses.items():
            if filename.strip().lower() == "instance.md":
                content = self._read_instance()
                access_context_parts.append(f"### {label} (Working Memory):\n{content}")
            else:
                try:
                    content = load_markdown(str(reservoir_dir / filename))
                    access_context_parts.append(f"### {label}:\n{content}")
                except Exception as e:
                    logging.warning(
                        f"Could not load reservoir '{label}' from file '{filename}': {e}"
                    )
        access_context = "\n\n".join(access_context_parts)

        full_prompt = (
            f"Protocol: {protocol.name}\n"
            f"Instructions:\n{protocol.prompt}\n\n"
            f"Access Contexts:\n{access_context}\n\n"
            f"User Input:\n{user_input}\n\n"
            f"Current Instance Context:\n{instance_content}\n"
        )

        original_prompt = self.system_prompt_generator.generate_prompt
        self.system_prompt_generator.generate_prompt = lambda: full_prompt

        agent_input = self.input_schema(chat_message=full_prompt)
        stream_response = ""
        async for partial in self.run_async(agent_input):
            stream_response += partial.chat_message
        result_text = stream_response.strip()
        self.system_prompt_generator.generate_prompt = original_prompt

        self._append_to_instance(f"{protocol.name} Output", result_text)
        return result_text

    def run_chain(
        self, user_input: str, protocols: List[Protocol], reservoir_dir: Path
    ) -> Dict[str, Any]:
        """
        Runs protocols sequentially.
        Re-initializes instance.md with the user input.
        Returns a mapping from protocol names to their outputs.
        """
        self._write_instance(
            "# Internal Reservoir Instance\n\n[User Input]:\n" + user_input + "\n"
        )

        results = {}
        for protocol in protocols:
            if not protocol.include_in_chain:
                print(f"Skipping protocol '{protocol.name}' (flag set to False).")
                results[protocol.name] = ""
                continue
            try:
                output = self.run_protocol(user_input, protocol, reservoir_dir)
                results[protocol.name] = output
                print(f"Protocol '{protocol.name}' executed successfully.")
            except Exception as err:
                results[protocol.name] = f"Error: {err}"
                print(f"Protocol '{protocol.name}' failed: {err}")
        return results

    async def run_chain_async(
        self, user_input: str, protocols: List[Protocol], reservoir_dir: Path
    ) -> Dict[str, Any]:
        """
        Asynchronous version of run_chain.
        """
        self._write_instance(
            "# Internal Reservoir Instance\n\n[User Input]:\n" + user_input + "\n"
        )

        results = {}
        for protocol in protocols:
            try:
                output = await self.run_protocol_async(
                    user_input, protocol, reservoir_dir
                )
                results[protocol.name] = output
                print(f"Async Protocol '{protocol.name}' executed successfully.")
            except Exception as err:
                results[protocol.name] = f"Error: {err}"
                print(f"Async Protocol '{protocol.name}' failed: {err}")
        return results
