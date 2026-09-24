from deepcurrent_local_mcp.policy import bound_output


def test_nested_artifact_output_is_bounded() -> None:
    payload = {
        "rows": [{"id": index} for index in range(100)],
        "metadata": {f"field-{index}": index for index in range(100)},
    }

    bounded = bound_output(payload)

    assert len(bounded["rows"]) == 25
    assert len(bounded["metadata"]) == 50
