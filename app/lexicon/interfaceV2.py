from typing import Any, Dict, Optional, Union
from mypy_extensions import TypedDict


class LexiconItemInterface(TypedDict, total=True):
    form: str
    lemma: str
    pos: str  # or with capital letters POS ?
    gloss: str
    features: Dict[str, Any]  # when no features, equal to None ? or empty dict ?
    frequency: int


tokenWithoutFeatures = LexiconItemInterface(
    form="eating",
    lemma="eat",
    pos="VERB",
    gloss="manger",
    frequency=178,
    features={},
)

tokenWithFeatures = LexiconItemInterface(
    form="eating",
    lemma="eat",
    pos="VERB",
    gloss="manger",
    frequency=178,
    features={"featureInt": 212, "featureFloat": 0.2113, "featureStr": "qwerty"},
)
