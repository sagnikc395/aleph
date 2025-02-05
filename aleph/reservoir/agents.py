from asyncio import Protocol
from datetime import datetime
from typing import Dict, Optional

from aleph.reservoir.abstraction import AbstractionNode


class GodOfWhatIs:
    """
    Handles data generation and transformation.
    """
    def run(
        self, protocol: Protocol, input_data: Dict, context: Dict
    ) -> Optional[AbstractionNode]:
        # Simulate protocol execution
        print(f"God of What Is: Running {protocol.name} on input data.")
        content = f"Processed {input_data.get('content', '')}"
        metadata = {
            "creation_time": datetime.now().isoformat(),
            "protocol": protocol.name,
            "version": protocol.version,
        }
        return AbstractionNode(content, metadata)


class GodOfWhatIsNot:
    """
    validates and refines the results.
    """

    def validate(
        self, node: AbstractionNode, context: Dict
    ) -> Optional[AbstractionNode]:
        # Simulate validation
        print(f"God of What Is Not: Validating node {node.id}.")
        if node.content and len(node.content) > 0:
            return node
        else:
            print("Validation failed: Empty content.")
            return None
