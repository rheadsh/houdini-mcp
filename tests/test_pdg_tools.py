import types


def _work_item(item_id, name, state, failed=False, logs=None, outputs=None):
    return types.SimpleNamespace(
        id=lambda: item_id,
        index=lambda: item_id,
        name=lambda: name,
        state=lambda: state,
        isFailed=lambda: failed,
        logMessages=lambda: logs or [],
        outputFiles=lambda: outputs or [],
    )


def test_pdg_workitems_lists_defensive_metadata(mock_hou):
    items = [
        _work_item(1, "item1", "Cooked", outputs=["/tmp/a.bgeo"]),
        _work_item(2, "item2", "Failed", failed=True, logs=["boom"]),
    ]
    top = types.SimpleNamespace(workItems=lambda: items)
    mock_hou.node = lambda p: top

    from houdini_side.tools.pdg import _pdg_workitems

    result = _pdg_workitems("/obj/topnet1")

    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["workitems"][0]["outputs"] == ["/tmp/a.bgeo"]
    assert result["data"]["workitems"][1]["state"] == "Failed"


def test_pdg_failed_items_filters_and_includes_logs(mock_hou):
    items = [
        _work_item(1, "good", "Cooked", failed=False),
        _work_item(2, "bad", "CookFailed", failed=True, logs=["failed log"]),
    ]
    top = types.SimpleNamespace(workItems=lambda: items)
    mock_hou.node = lambda p: top

    from houdini_side.tools.pdg import _pdg_failed_items

    result = _pdg_failed_items("/obj/topnet1")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["failed_items"][0]["name"] == "bad"
    assert result["data"]["failed_items"][0]["logs"] == ["failed log"]


def test_pdg_failed_items_detects_failed_state_without_is_failed(mock_hou):
    failed = types.SimpleNamespace(
        id=lambda: 4,
        index=lambda: 4,
        name=lambda: "state_failed",
        state=lambda: "Failed",
        log=lambda: "inline failure",
    )
    top = types.SimpleNamespace(workItems=lambda: [failed])
    mock_hou.node = lambda p: top

    from houdini_side.tools.pdg import _pdg_failed_items

    result = _pdg_failed_items("/obj/topnet1")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["failed_items"][0]["logs"] == ["inline failure"]


def test_pdg_logs_can_return_failed_only(mock_hou):
    items = [
        _work_item(1, "good", "Cooked", failed=False, logs=["ok log"]),
        _work_item(2, "bad", "Failed", failed=True, logs=["bad log"]),
    ]
    top = types.SimpleNamespace(workItems=lambda: items)
    mock_hou.node = lambda p: top

    from houdini_side.tools.pdg import _pdg_logs

    result = _pdg_logs("/obj/topnet1", failed_only=True)

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["logs"][0]["name"] == "bad"
    assert result["data"]["logs"][0]["logs"] == ["bad log"]


def test_pdg_workitems_can_target_child_node(mock_hou):
    item = _work_item(1, "child_item", "Cooked")
    child = types.SimpleNamespace(workItems=lambda: [item])
    net = types.SimpleNamespace(node=lambda name: child if name == "ropfetch1" else None)
    mock_hou.node = lambda p: net

    from houdini_side.tools.pdg import _pdg_workitems

    result = _pdg_workitems("/obj/topnet1", node_name="ropfetch1")

    assert result["success"] is True
    assert result["data"]["node"] == "ropfetch1"
    assert result["data"]["count"] == 1
