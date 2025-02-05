#!/usr/bin/env python

from pathlib import Path
import instructor
import os

from aleph.ui import obtain_user_input


# ------------------------------------------------------------------------------
# Entrypoint Examples: Synchronous and Asynchronous Chain Execution
# ------------------------------------------------------------------------------
def main():
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    # Instantiate your Anthropic client – replace "my_api_key" with your actual API key.

    anthropic_api_key = os.getenv("ANTHROPIC_KEY")
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    agent_client = instructor.from_anthropic(client)

    config = BaseAgentConfig(
        client=agent_client,
        model="claude-3-5-sonnet-20241022",  # Adjust the model name as needed.
        temperature=0.0,
        memory=AgentMemory(),
    )

    instance_path = Path("instance.md")
    agent = AgentChain(config=config, instance_file=str(instance_path))
    protocols = [
        extract_protocol,
        atomize_protocol,
        reflect_protocol,
        integrate_protocol,
    ]

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
