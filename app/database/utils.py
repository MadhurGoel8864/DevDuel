from typing import Annotated
from uuid import uuid4

from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]
UUIDStr = Annotated[str, BeforeValidator(str)]


def generate_uuid() -> str:
    """
    Function to generate a uuid4

    Returns:
        str: a uuid 4 as string
    """
    return uuid4().hex
