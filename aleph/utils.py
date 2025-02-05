# ------------------------------------------------------------------------------
# Utility: Load a Markdown file from a given filepath.
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Protocol

from aleph.main import PATTERNS_DIR


def load_markdown(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")
    return path.read_text(encoding="utf-8").strip()


# ------------------------------------------------------------------------------
# Example merge function (if desired by a protocol)
# ------------------------------------------------------------------------------
def merge_with_separator(current: str, new: str) -> str:
    separator = "\n" + ("=" * 60) + "\n"
    return current + separator + new


integrate_protocol = Protocol(
    name="Integrate",
    prompt_file=str(PATTERNS_DIR / "Integrate.md"),
    include_in_chain=True,
    accesses={
        "Reflect Protocol Output": "instance.md",  # Use instance.md for reflect output.
        "New Abstractions": "instance.md",  # Use instance.md for new atomizations.
        "Abstraction Theory Picture": "Abstraction_Theory_Picture.md",
        "Abstraction Theory": "Abstraction_Theory.md",
        "Intuition Reservoir": "Intuition_Reservoir.md",
    },
    merge_context=merge_with_separator,
)

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
    requires_commentary=False,  # <<-- commentary input will be requested
)
