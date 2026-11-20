"""Load the checked-in schemas and validate structural and semantic invariants."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[1] / "schema"


def validator(name):
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    quote = json.loads((SCHEMAS / "receipt-v1.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource("receipt-v1.json", Resource.from_contents(quote))
    return Draft202012Validator(schema, registry=registry)


def validate_quote(receipt, structure):
    structure.validate(receipt)
    evidence = receipt["evidence"]
    if "observed_commit" in evidence and evidence["observed_commit"] != receipt["claim"]["requested_commit"]:
        raise ValidationError("observed commit differs from the requested commit")
    if "lines" in evidence and evidence["lines"]["end"] < evidence["lines"]["start"]:
        raise ValidationError("quotation line range is inverted")
