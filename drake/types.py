from dataclasses import dataclass, field

@dataclass
class Type:
    name: str
    params: tuple = ()
