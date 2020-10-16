from typing import TypedDict


class WhatsitInterface(TypedDict, total=False):
    whatsit_id: int
    name: str
    purpose: str
