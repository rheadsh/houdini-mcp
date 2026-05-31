import types


def test_lop_layer_stack_requires_pxr_cleanly(mock_hou, monkeypatch):
    from houdini_side.tools import solaris

    monkeypatch.setattr(solaris, "_PXR_AVAILABLE", False)
    result = solaris._lop_layer_stack("/stage/usd")

    assert result["success"] is False
    assert result["error_type"] == "RuntimeError"
    assert "pxr" in result["error"]


def test_lop_layer_stack_lists_used_layers(mock_hou, monkeypatch):
    from houdini_side.tools import solaris

    layers = [
        types.SimpleNamespace(
            identifier="anon:root",
            realPath="",
            anonymous=True,
            dirty=False,
        ),
        types.SimpleNamespace(
            identifier="/show/asset.usd",
            realPath="/show/asset.usd",
            anonymous=False,
            dirty=True,
        ),
    ]
    stage = types.SimpleNamespace(GetUsedLayers=lambda: layers)
    node = types.SimpleNamespace(stage=lambda: stage)
    mock_hou.node = lambda path: node
    monkeypatch.setattr(solaris, "_PXR_AVAILABLE", True)

    result = solaris._lop_layer_stack("/stage/usd")

    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["layers"][0]["anonymous"] is True
    assert result["data"]["layers"][1]["dirty"] is True


def test_lop_prim_relationships_lists_targets(mock_hou, monkeypatch):
    from houdini_side.tools import solaris

    class _Target:
        def __init__(self, path):
            self.path = path

    rel = types.SimpleNamespace(
        GetName=lambda: "material:binding",
        GetTargets=lambda: [_Target("/Looks/plastic")],
    )
    prim = types.SimpleNamespace(
        IsValid=lambda: True,
        GetRelationships=lambda: [rel],
    )
    stage = types.SimpleNamespace(GetPrimAtPath=lambda path: prim)
    node = types.SimpleNamespace(stage=lambda: stage)
    mock_hou.node = lambda path: node
    monkeypatch.setattr(solaris, "_PXR_AVAILABLE", True)

    result = solaris._lop_prim_relationships("/stage/usd", "/World/geo")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["relationships"][0]["name"] == "material:binding"
    assert result["data"]["relationships"][0]["targets"] == ["/Looks/plastic"]

