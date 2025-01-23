#!/usr/bin/env python
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

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Type
import instructor
from pydantic import BaseModel
import re
import os
import tempfile
import click  # pip install click


# ------------------------------------------------------------------------------
# Utility: Load a Markdown file from a given filepath.
# ------------------------------------------------------------------------------
def load_markdown(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")
    return path.read_text(encoding="utf-8").strip()

# ------------------------------------------------------------------------------
# Protocol Definition
# ------------------------------------------------------------------------------
class Protocol:
    """
    Represents a protocol step.
    
    Attributes:
        name (str): The protocol name.
        prompt (str): Full protocol instructions loaded from a Markdown file in the patterns folder.
        accesses (Optional[Dict[str, str]]): Dictionary mapping descriptive labels to reservoir filenames (from reservoir/).
        include_in_chain (bool): If False, the protocol is skipped.
        merge_context (Callable[[str, str], str]): Function used to merge this protocol's output with the working memory.
    """
    def __init__(
        self,
        name: str,
        prompt_file: str,
        include_in_chain: bool = True,
        accesses: Optional[Dict[str, str]] = None,
        merge_context: Optional[Callable[[str, str], str]] = None,
        requires_commentary: bool = False,   # <<-- new parameter
    ):
        self.name = name
        self.prompt = load_markdown(prompt_file)
        self.accesses = accesses or {}
        self.include_in_chain = include_in_chain
        self.merge_context = merge_context or (lambda current, new: current + "\n\n" + new)
        self.requires_commentary = requires_commentary   # <<-- store new flag

    
    def get_all_access_context(self, reservoir_dir: Path) -> str:
        """
        Loads and concatenates all reservoir guidance from the reservoir directory
        according to the accesses mapping.
        """
        context_parts = []
        for label, filename in self.accesses.items():
            try:
                content = load_markdown(str(reservoir_dir / filename))
                context_parts.append(f"### {label}:\n{content}")
            except Exception as e:
                logging.warning(f"Could not load reservoir '{label}' from file '{filename}': {e}")
        return "\n\n".join(context_parts)

# ------------------------------------------------------------------------------
# AgentChain: Extended Agent Using a Single Working Memory File (instance.md)
# ------------------------------------------------------------------------------
# Import base agent components; adjust the paths as needed.
from atomic_agents.agents.base_agent import BaseIOSchema, BaseAgent, BaseAgentConfig, BaseAgentInputSchema, BaseAgentOutputSchema
from atomic_agents.lib.components.agent_memory import AgentMemory
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator

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
            {"role": "system", "content": self.system_prompt_generator.generate_prompt()},
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
    
    def run_protocol(self, user_input: str, protocol: Protocol, reservoir_dir: Path) -> str:
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
                    logging.warning(f"Could not load reservoir '{label}' from file '{filename}': {e}")
        access_context = "\n\n".join(access_context_parts)

        # Build the full prompt; if commentary is provided, insert it as its own section before the user input.
        commentary_section = f"\n\nCommentary for {protocol.name}:\n{commentary_text}" if commentary_text else ""
        
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


    
    async def run_protocol_async(self, user_input: str, protocol: Protocol, reservoir_dir: Path) -> str:
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
                    logging.warning(f"Could not load reservoir '{label}' from file '{filename}': {e}")
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
    
    def run_chain(self, user_input: str, protocols: List[Protocol], reservoir_dir: Path) -> Dict[str, Any]:
        """
        Runs protocols sequentially.
        Re-initializes instance.md with the user input.
        Returns a mapping from protocol names to their outputs.
        """
        self._write_instance("# Internal Reservoir Instance\n\n[User Input]:\n" + user_input + "\n")
        
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

    
    async def run_chain_async(self, user_input: str, protocols: List[Protocol], reservoir_dir: Path) -> Dict[str, Any]:
        """
        Asynchronous version of run_chain.
        """
        self._write_instance("# Internal Reservoir Instance\n\n[User Input]:\n" + user_input + "\n")
        
        results = {}
        for protocol in protocols:
            try:
                output = await self.run_protocol_async(user_input, protocol, reservoir_dir)
                results[protocol.name] = output
                print(f"Async Protocol '{protocol.name}' executed successfully.")
            except Exception as err:
                results[protocol.name] = f"Error: {err}"
                print(f"Async Protocol '{protocol.name}' failed: {err}")
        return results

# ------------------------------------------------------------------------------
# Example merge function (if desired by a protocol)
# ------------------------------------------------------------------------------
def merge_with_separator(current: str, new: str) -> str:
    separator = "\n" + ("=" * 60) + "\n"
    return current + separator + new

def obtain_user_input(instance_path: Path) -> str:
    """
    Checks the instance file for a '[User Input]:' section.
    If found and non-empty, returns the user input.
    Otherwise, opens the user's default editor (via click.edit)
    so the user can input or paste a large block of text.
    Before returning, lines starting with '#' are filtered out.
    The resulting text is stored in the instance file under '[User Input]:'
    and then returned.
    """
    content = instance_path.read_text(encoding="utf-8") if instance_path.exists() else ""
    match = re.search(r"\[User Input\]:\s*(.*?)\s*(?:\n---|\Z)", content, re.DOTALL)
    user_input = match.group(1).strip() if match else ""
    
    if user_input:
        return user_input

    print("No '[User Input]:' section found or it's empty.\n"
          "An editor will open for you to paste/type your raw input text. Save and close the editor when done.")
    
    initial_content = "# input text:\n\n"
    fd, temp_path = tempfile.mkstemp(suffix=".md", text=True)
    os.close(fd)
    
    edited_text = click.edit(initial_content)
    if edited_text is None:
        print("Editor was closed without saving any content. Exiting.")
        exit(1)
    # Remove lines starting with '#' and strip extraneous whitespace.
    filtered = "\n".join([line for line in edited_text.splitlines() if not line.strip().startswith("#")]).strip()
    user_input = filtered
    
    new_section = f"[User Input]:\n{user_input}\n\n---\n"
    if content:
        if "[User Input]:" in content:
            parts = re.split(r"\[User Input\]:", content, maxsplit=1)
            content = parts[0].strip() + "\n\n" + new_section
        else:
            content += "\n\n" + new_section
    else:
        content = "# Internal Reservoir Instance\n\n" + new_section
    
    instance_path.write_text(content, encoding="utf-8")
    return user_input

def obtain_commentary(protocol_name: str) -> str:
    """
    Opens an editor for the user to enter commentary associated with a given protocol.
    Lines starting with '#' are filtered out. Returns the stripped commentary.
    """
    print(f"Protocol '{protocol_name}' requires commentary.\n"
          "An editor will open for you to paste/type your commentary. Save and close the editor when done.")
    initial_content = f"# Commentary for protocol {protocol_name} :\n\n"
    fd, temp_path = tempfile.mkstemp(suffix=".md", text=True)
    os.close(fd)
    
    edited_text = click.edit(initial_content)
    if edited_text is None:
        return ""
    filtered = "\n".join([line for line in edited_text.splitlines() if not line.strip().startswith("#")]).strip()
    return filtered


# ------------------------------------------------------------------------------
# Instantiate Protocol Objects from the patterns Directory
# ------------------------------------------------------------------------------
PATTERNS_DIR = Path("./Patterns")
RESERVOIR_DIR = Path("./Reservoir")

# Configure protocols with their instruction files and the reservoirs they access.
# Note that any reference that previously pointed to output files (e.g., "Atomize_Output.md")
# is now replaced by "instance.md" since all outputs are in the same working memory.
extract_protocol = Protocol(
    name="Extract",
    prompt_file=str(PATTERNS_DIR / "Extract.md"),
    include_in_chain=True,  # Set to False to skip if desired.
    accesses={"Intuition Reservoir": "Intuition_Reservoir.md"}, 
    merge_context=merge_with_separator,
)

atomize_protocol = Protocol(
    name="Atomize",
    prompt_file=str(PATTERNS_DIR / "Atomize.md"),
    include_in_chain=True,
    accesses={"Intuition Reservoir": "Intuition_Reservoir.md"},
    merge_context=merge_with_separator,
)

reflect_protocol = Protocol(
    name="Reflect",
    prompt_file=str(PATTERNS_DIR / "Reflect.md"),
    include_in_chain=True,
    accesses={
        "Newly Atomized Abstractions": "instance.md",  # Use instance.md for previous outputs.
        "Abstraction Theory": "Abstraction_Theory.md",
        "Intuition Reservoir": "Intuition_Reservoir.md",
    },
    merge_context=merge_with_separator,
    requires_commentary=False   # <<-- commentary input will be requested
)


integrate_protocol = Protocol(
    name="Integrate",
    prompt_file=str(PATTERNS_DIR / "Integrate.md"),
    include_in_chain=True,
    accesses={
        "Reflect Protocol Output": "instance.md",  # Use instance.md for reflect output.
        "New Abstractions": "instance.md",          # Use instance.md for new atomizations.
        "Abstraction Theory Picture": "Abstraction_Theory_Picture.md",
        "Abstraction Theory": "Abstraction_Theory.md",
        "Intuition Reservoir": "Intuition_Reservoir.md",
    },
    merge_context=merge_with_separator,
)

# ------------------------------------------------------------------------------
# Entrypoint Examples: Synchronous and Asynchronous Chain Execution
# ------------------------------------------------------------------------------

def main():
    import anthropic
    from dotenv import load_dotenv

    load_dotenv() 
    # Instantiate your Anthropic client – replace "my_api_key" with your actual API key.

    anthropic_api_key = os.getenv('ANTHROPIC_KEY')
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    agent_client = instructor.from_anthropic(client)

    config = BaseAgentConfig(
        client=agent_client,
        model="claude-3-5-sonnet-20241022",  # Adjust the model name as needed.
        temperature=0.0,
        memory=AgentMemory()
    )

    instance_path = Path("instance.md")
    agent = AgentChain(config=config, instance_file=str(instance_path))
    protocols = [extract_protocol, atomize_protocol, reflect_protocol, integrate_protocol]

    # Use the instance file to obtain raw user input.
    user_input = obtain_user_input(instance_path)

    try:
        results = agent.run_chain(user_input, protocols, RESERVOIR_DIR)
    except Exception as e:
        print(f"Chain execution encountered an error: {e}")
        return

    print("\n=== Protocol Results ===")
    for proto_name, output in results.items():
        print(f"\n[{proto_name}]:\n{output}")

    print("\n=== Final Internal Reservoir (instance.md) ===")
    print(agent._read_instance())

if __name__ == "__main__":
    main()
