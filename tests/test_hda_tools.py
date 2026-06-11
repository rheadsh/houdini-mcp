import types


def _make_defn(node_type, version, file_path, preferred=False):
    return types.SimpleNamespace(
        nodeTypeName=lambda: node_type,
        description=lambda: f"{node_type} label",
        version=lambda: version,
        libraryFilePath=lambda: file_path,
        isPreferred=lambda: preferred,
    )


def test_hda_versions_lists_loaded_versions(mock_hou):
    defns = [
        _make_defn("studio_asset::1.0", "1.0", "/hda/studio_asset_1.hda"),
        _make_defn("studio_asset::2.0", "2.0", "/hda/studio_asset_2.hda", True),
    ]
    mock_hou.hda.loadedFiles = lambda: ["/hda/studio_asset.hda"]
    mock_hou.hda.definitionsInFile = lambda path: defns

    from houdini_side.tools.hda import _hda_versions
    result = _hda_versions()

    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["versions"][1]["version"] == "2.0"
    assert result["data"]["versions"][1]["is_preferred"] is True


def test_hda_versions_filters_by_node_type(mock_hou):
    defns = [
        _make_defn("studio_asset::1.0", "1.0", "/hda/studio_asset.hda"),
        _make_defn("other_asset::1.0", "1.0", "/hda/other_asset.hda"),
    ]
    mock_hou.hda.loadedFiles = lambda: ["/hda/assets.hda"]
    mock_hou.hda.definitionsInFile = lambda path: defns

    from houdini_side.tools.hda import _hda_versions
    result = _hda_versions("studio_asset::1.0")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["versions"][0]["node_type"] == "studio_asset::1.0"


def test_hda_versions_falls_back_to_hda_definition(mock_hou):
    mock_hou.hda.loadedFiles = lambda: []
    defn = _make_defn("fallback_test", "3.0", "/tmp/fallback.hda")
    mock_hou.hdaDefinition = lambda cat, name, ver: defn if name == "fallback_test" else None

    from houdini_side.tools.hda import _hda_versions
    result = _hda_versions("fallback_test")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["versions"][0]["file"] == "/tmp/fallback.hda"


def test_hda_list_returns_empty_when_unavailable(mock_hou):
    # Remove hda attr to simulate unavailability
    if hasattr(mock_hou, 'hda'):
        delattr(mock_hou, 'hda')
    from houdini_side.tools.hda import _hda_list
    result = _hda_list()
    assert result["success"] is True
    assert result["data"]["hdas"] == []

