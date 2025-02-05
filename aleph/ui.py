import os
from pathlib import Path
import re
import tempfile

import click


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
    content = (
        instance_path.read_text(encoding="utf-8") if instance_path.exists() else ""
    )
    match = re.search(r"\[User Input\]:\s*(.*?)\s*(?:\n---|\Z)", content, re.DOTALL)
    user_input = match.group(1).strip() if match else ""

    if user_input:
        return user_input

    print(
        "No '[User Input]:' section found or it's empty.\n"
        "An editor will open for you to paste/type your raw input text. Save and close the editor when done."
    )

    initial_content = "# input text:\n\n"
    fd, temp_path = tempfile.mkstemp(suffix=".md", text=True)
    os.close(fd)

    edited_text = click.edit(initial_content)
    if edited_text is None:
        print("Editor was closed without saving any content. Exiting.")
        exit(1)
    # Remove lines starting with '#' and strip extraneous whitespace.
    filtered = "\n".join(
        [line for line in edited_text.splitlines() if not line.strip().startswith("#")]
    ).strip()
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
    print(
        f"Protocol '{protocol_name}' requires commentary.\n"
        "An editor will open for you to paste/type your commentary. Save and close the editor when done."
    )
    initial_content = f"# Commentary for protocol {protocol_name} :\n\n"
    fd, temp_path = tempfile.mkstemp(suffix=".md", text=True)
    os.close(fd)

    edited_text = click.edit(initial_content)
    if edited_text is None:
        return ""
    filtered = "\n".join(
        [line for line in edited_text.splitlines() if not line.strip().startswith("#")]
    ).strip()
    return filtered
