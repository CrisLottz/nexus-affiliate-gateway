"""Request-body validation with Pydantic."""

from __future__ import annotations

from flask import abort, jsonify, make_response, request
from pydantic import BaseModel, ValidationError


def parse_body[M: BaseModel](model: type[M]) -> M:
    """Validate the JSON body against `model`, or abort with 422 and the field errors."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(make_response(jsonify(error="invalid_json", message="Expected a JSON object"), 400))
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        fields = {".".join(str(p) for p in err["loc"]) or "_": err["msg"] for err in exc.errors()}
        abort(make_response(jsonify(error="validation_error", fields=fields), 422))
