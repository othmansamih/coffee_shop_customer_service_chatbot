from typing import Protocol, List, Dict, Any

class ProtocolAgent(Protocol):
    def get_response(messages : List[Dict[str, Any]]) -> Dict[str, Any]:
        ...
