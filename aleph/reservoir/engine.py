from asyncio import Protocol
from typing import Dict, Optional
from aleph.reservoir.abstraction import AbstractionNode


class ExecutionEngine:
    """
    Orchestrates protocol execution. It looks up protocols, instantiates agents, creates context frames, and runs the protocol steps.
    """

    def __init__(self, protocol_registry: Dict[str, Protocol], memory_manager):
        self.protocol_registry = protocol_registry
        self.memory_manager = memory_manager

    def execute_protocol(
        self, protocol_name: str, input_data: Dict, context: Dict
    ) -> Optional[AbstractionNode]:
        # Lookup protocol
        protocol = self.protocol_registry.get(protocol_name)
        if not protocol:
            print(f"Protocol {protocol_name} not found in registry.")
            return None

        print(f"Executing {protocol_name}...")

        # Instantiate agents (God of What Is and God of What Is Not)
        god_of_what_is = GodOfWhatIs()
        god_of_what_is_not = GodOfWhatIsNot()

        # Create context frame
        context_frame = {
            "current_data": input_data,
            "invocation_protocol": protocol,
            "caller_pattern": context.get("caller_pattern", "Unknown"),
            "agent_roles": {"primary": god_of_what_is, "secondary": god_of_what_is_not},
            "memory_pointers": [],
        }

        # Run protocol steps
        result = god_of_what_is.run(protocol, input_data, context_frame)
        validated_result = god_of_what_is_not.validate(result, context_frame)

        # Store result in memory
        if validated_result:
            self.memory_manager.store(validated_result)
            return validated_result
        else:
            print(f"Validation failed for {protocol_name}.")
            return None
