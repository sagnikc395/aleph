from asyncio import Protocol
from typing import Dict, List, Optional
import uuid
from datetime import datetime

from aleph.reservoir.engine import ExecutionEngine
from aleph.reservoir.orcheastrator import MemoryManager
from aleph.reservoir.registry import ProtocolRegistry


if __name__ == "__main__":
    # Initialize components
    memory_manager = MemoryManager()
    protocol_registry = ProtocolRegistry()

    # Define a protocol
    extract_protocol = Protocol(
        name="Extract",
        version="1.0",
        input_spec={"content": "str"},
        output_spec={"content": "str"},
        triggers=["ingest"],
    )
    protocol_registry.register(extract_protocol)

    # Initialize execution engine
    execution_engine = ExecutionEngine(protocol_registry.protocols, memory_manager)

    # Execute a protocol
    input_data = {"content": "Sample text to process."}
    context = {"caller_pattern": "Perceive"}
    result = execution_engine.execute_protocol("Extract", input_data, context)

    if result:
        print(f"Resulting node: {result}")
    else:
        print("Protocol execution failed.")
