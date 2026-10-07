"""JSON Schema for the model's tags (a small subset: type, enum, required, properties, items, anyOf) and a
standard-library validator for it. 07_build.py writes this schema, extended with the record fields, to data/schema.json."""

TAGS_SCHEMA = {
    "type": "object",
    "required": ["scene_summary", "people", "figure_count", "places", "objects", "actions", "setting",
                 "time_of_day", "uncertain", "passage_check"],
    "properties": {
        "scene_summary": {"type": "string", "minLength": 10},
        "people": {"type": "array", "items": {
            "type": "object", "required": ["label", "identity", "basis"],
            "properties": {"label": {"type": "string", "minLength": 1},
                           "identity": {"type": ["string", "null"]},
                           "basis": {"type": "string", "enum": ["passage", "none"]}}}},
        "figure_count": {"anyOf": [{"type": "integer", "minimum": 0}, {"type": "string", "enum": ["crowd"]}]},
        "places": {"type": "array", "items": {"type": "string"}},
        "objects": {"type": "array", "items": {"type": "string"}},
        "actions": {"type": "array", "items": {"type": "string"}},
        "setting": {"type": "string", "enum": ["indoor", "outdoor", "mixed"]},
        "time_of_day": {"type": "string", "enum": ["day", "night", "unclear"]},
        "mood": {"type": "string"},
        "uncertain": {"type": "array", "items": {"type": "string"}},
        "passage_check": {"type": "object", "required": ["verdict", "note"], "properties": {
            "verdict": {"type": "string", "enum": ["agrees", "partly", "disagrees", "no_reference"]},
            "note": {"type": "string"}}},
        "proposed_passage": {"type": ["string", "null"]},
    },
}

_TYPES = {"object": dict, "array": list, "string": str, "null": type(None), "integer": int, "number": (int, float)}


def validate(value, schema, path="$"):
    """List of error strings; empty when the value fits the schema."""
    if "anyOf" in schema:
        errs = [validate(value, s, path) for s in schema["anyOf"]]
        return [] if any(not e for e in errs) else [f"{path}: matches none of the allowed shapes"]
    types = schema.get("type")
    if types:
        types = types if isinstance(types, list) else [types]
        if isinstance(value, bool) or not any(isinstance(value, _TYPES[t]) for t in types):
            return [f"{path}: expected {'/'.join(types)}, got {type(value).__name__}"]
    errs = []
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errs.append(f"{path}: too short")
    if isinstance(value, int) and not isinstance(value, bool) and value < schema.get("minimum", value):
        errs.append(f"{path}: below minimum")
    if isinstance(value, dict):
        errs += [f"{path}.{k}: required" for k in schema.get("required", []) if k not in value]
        for k, s in schema.get("properties", {}).items():
            if k in value:
                errs += validate(value[k], s, f"{path}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


if __name__ == "__main__":
    good = {"scene_summary": "A man lowered through a roof.", "people": [{"label": "man", "identity": None, "basis": "none"}],
            "figure_count": "crowd", "places": [], "objects": [], "actions": [], "setting": "indoor",
            "time_of_day": "day", "uncertain": [], "passage_check": {"verdict": "agrees", "note": ""}}
    assert validate(good, TAGS_SCHEMA) == []
    assert validate({**good, "figure_count": 3.5}, TAGS_SCHEMA)
    assert validate({**good, "setting": "sea"}, TAGS_SCHEMA)
    assert validate({k: v for k, v in good.items() if k != "people"}, TAGS_SCHEMA)
    assert validate({**good, "people": [{"label": "x", "identity": "David", "basis": "visual"}]}, TAGS_SCHEMA)
    print("schema.py self-test passed")
