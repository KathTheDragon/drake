from dataclasses import dataclass

@dataclass
class VM:
    bytecode: bytesarray
    stack: list = field(default_factory=list, init=False)
    ip: int = field(init=False)
