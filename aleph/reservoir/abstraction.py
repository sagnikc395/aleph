# Define Abstraction Node
from typing import Dict
import uuid


class AbstractionNode:
    """
    Represents a node in the memory hierarchy. Each node has a unique ID, content, metadata, and relationships (parent/child).
    """

    def __init__(self, content: str, metadata: Dict):
        self.id = str(uuid.uuid4())  # Unique ID
        self.content = content  # Content payload
        self.metadata = metadata  # Metadata (e.g., creation time, tags)
        self.children = []  # Child nodes
        self.parent = None  # Parent node

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def __repr__(self):
        return f"AbstractionNode(id={self.id}, content={self.content[:20]}...)"
