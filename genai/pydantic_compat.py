from __future__ import annotations

import json
from typing import Any, TypeVar


ModelT = TypeVar("ModelT")


def model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


def model_to_json(model: Any, *, indent: int | None = None) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json(indent=indent)
    return model.json(indent=indent)


def model_validate(model_class: type[ModelT], payload: dict[str, Any]) -> ModelT:
    if hasattr(model_class, "model_validate"):
        return model_class.model_validate(payload)
    return model_class.parse_obj(payload)


def model_validate_json(model_class: type[ModelT], payload: str) -> ModelT:
    if hasattr(model_class, "model_validate_json"):
        return model_class.model_validate_json(payload)
    return model_class.parse_raw(payload)


def model_copy(model: Any, *, update: dict[str, Any]) -> Any:
    if hasattr(model, "model_copy"):
        return model.model_copy(update=update)
    return model.copy(update=update)
