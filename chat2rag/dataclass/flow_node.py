from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Condition:
    id: Optional[int]
    trigger: str = ""
    transition_node_id: str = ""
    transition_node_state_name: str = ""


@dataclass
class Node:
    id: str = ""
    node_type: str = ""
    label: str = ""
    is_auto: bool = False
    conditions: List[Condition] = field(default_factory=list)
    emoji: str = ""
    action: str = ""
    response: str = ""
    state_name: str = ""
