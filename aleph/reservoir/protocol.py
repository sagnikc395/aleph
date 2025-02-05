from typing import Dict, List


class Protocol:
    """
    Defines a protocol with its name, version, input/output specifications, and invocation triggers.
    """

    def __init__(
        self,
        name: str,
        version: str,
        input_spec: Dict,
        output_spec: Dict,
        triggers: List[str],
    ):
        self.name = name
        self.version = version
        self.input_spec = input_spec
        self.output_spec = output_spec
        self.triggers = triggers

    def __repr__(self):
        return f"Protocol(name={self.name}, version={self.version})"
