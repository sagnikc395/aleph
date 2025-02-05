# Define Protocol Registry
from asyncio import Protocol
from typing import Optional


class ProtocolRegistry:
    def __init__(self):
        self.protocols = {}

    def register(self, protocol: Protocol):
        self.protocols[protocol.name] = protocol
        print(f"Registered protocol: {protocol.name}")

    def get(self, protocol_name: str) -> Optional[Protocol]:
        return self.protocols.get(protocol_name)
