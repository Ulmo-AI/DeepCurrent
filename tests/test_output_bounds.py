from deepcurrent_local_mcp.plugins.official.helpers import _bound_output


def test_nested_artifact_output_is_bounded() -> None:
    payload = {
        "rows": [{"id": index} for index in range(100)],
        "metadata": {f"field-{index}": index for index in range(100)},
    }

    bounded = _bound_output(payload)

    assert len(bounded["rows"]) == 25
    assert len(bounded["metadata"]) == 50
