# ------------------------------------------------------------------------------
# Protocol Definition
# ------------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Callable, Dict, Optional
from aleph.utils import load_markdown


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
        requires_commentary: bool = False,  # <<-- new parameter
    ):
        self.name = name
        self.prompt = load_markdown(prompt_file)
        self.accesses = accesses or {}
        self.include_in_chain = include_in_chain
        self.merge_context = merge_context or (
            lambda current, new: current + "\n\n" + new
        )
        self.requires_commentary = requires_commentary  # <<-- store new flag

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
                logging.warning(
                    f"Could not load reservoir '{label}' from file '{filename}': {e}"
                )
        return "\n\n".join(context_parts)
