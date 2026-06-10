"""Houdini Digital Asset (HDA) management tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import resolve_output_path, as_text

_HDA_SUFFIXES = (".hda", ".hdanc", ".hdalc", ".otl", ".otlnc", ".otllc")


def _hda_list():
    try:
        def work():
            hda = getattr(hou, 'hda', None)
            if hda is None:
                return ok({"hdas": [], "note": "hou.hda not available"})
            files = hda.loadedFiles()
            result = []
            for f in files:
                for defn in hda.definitionsInFile(f):
                    result.append({
                        "file": f,
                        "node_type": defn.nodeTypeName(),
                        "label": defn.description(),
                        "version": defn.version(),
                    })
            return ok({"hdas": result, "count": len(result)})
        return dispatch(work, label="hda_list")
    except Exception as e:
        return err(e)


def _hda_info(hda_node_type: str):
    try:
        def work():
            # Try all major contexts
            defn = None
            for cat_fn in [hou.sopNodeTypeCategory, hou.objNodeTypeCategory,
                           hou.dopNodeTypeCategory, hou.lopNodeTypeCategory]:
                try:
                    defn = hou.hdaDefinition(cat_fn(), hda_node_type, None)
                    if defn:
                        break
                except Exception:
                    continue
            if defn is None:
                raise ValueError(f"HDA definition not found: {hda_node_type!r}")
            sections = list(defn.sections().keys())
            return ok({
                "node_type": hda_node_type,
                "label": defn.description(),
                "version": defn.version(),
                "sections": sections,
            })
        return dispatch(work, label="hda_info")
    except Exception as e:
        return err(e)


def _hda_versions(hda_node_type: "str | None" = None):
    try:
        def work():
            hda = getattr(hou, 'hda', None)
            versions = []
            seen = set()

            if hda is not None:
                for hda_file in hda.loadedFiles():
                    try:
                        definitions = hda.definitionsInFile(hda_file)
                    except Exception:
                        continue
                    for defn in definitions:
                        try:
                            node_type = defn.nodeTypeName()
                        except Exception:
                            node_type = ""
                        if hda_node_type and node_type != hda_node_type:
                            continue
                        item = {
                            "file": hda_file,
                            "node_type": node_type,
                            "label": getattr(defn, "description", lambda: "")(),
                            "version": getattr(defn, "version", lambda: "")(),
                            "is_preferred": bool(getattr(defn, "isPreferred", lambda: False)()),
                        }
                        key = (item["file"], item["node_type"], item["version"])
                        if key not in seen:
                            seen.add(key)
                            versions.append(item)

            if hda_node_type and not versions:
                for cat_fn in [hou.sopNodeTypeCategory, hou.objNodeTypeCategory,
                               hou.dopNodeTypeCategory, hou.lopNodeTypeCategory]:
                    try:
                        defn = hou.hdaDefinition(cat_fn(), hda_node_type, None)
                    except Exception:
                        continue
                    if defn is None:
                        continue
                    item = {
                        "file": getattr(defn, "libraryFilePath", lambda: "")(),
                        "node_type": getattr(defn, "nodeTypeName", lambda: hda_node_type)(),
                        "label": getattr(defn, "description", lambda: "")(),
                        "version": getattr(defn, "version", lambda: "")(),
                        "is_preferred": bool(getattr(defn, "isPreferred", lambda: False)()),
                    }
                    key = (item["file"], item["node_type"], item["version"])
                    if key not in seen:
                        versions.append(item)
                    break

            return ok({
                "node_type": hda_node_type,
                "versions": versions,
                "count": len(versions),
            })
        return dispatch(work, label="hda_versions")
    except Exception as e:
        return err(e)


def _hda_install(hda_path: str):
    try:
        def work():
            hda = getattr(hou, 'hda', None)
            if hda is None:
                raise RuntimeError("hou.hda module not available")
            hda.installFile(hda_path)
            return ok({"installed": hda_path})
        return dispatch(work, label="hda_install")
    except Exception as e:
        return err(e)


def _hda_uninstall(hda_node_type: str):
    try:
        def work():
            defn = None
            for cat_fn in [hou.sopNodeTypeCategory, hou.objNodeTypeCategory,
                           hou.dopNodeTypeCategory, hou.lopNodeTypeCategory]:
                try:
                    defn = hou.hdaDefinition(cat_fn(), hda_node_type, None)
                    if defn:
                        break
                except Exception:
                    continue
            if defn is None:
                raise ValueError(f"HDA not found: {hda_node_type!r}")
            defn.destroy()
            return ok({"uninstalled": hda_node_type})
        return dispatch(work, label="hda_uninstall")
    except Exception as e:
        return err(e)


def _hda_save(node_path: str, hda_file_path: "str | None" = None):
    try:
        def work():
            with hou.undos.group("mcp: save hda"):
                node = hou.node(node_path)
                if node is None:
                    raise ValueError(f"Node not found: {node_path!r}")
                defn = node.type().definition()
                if defn is None:
                    raise ValueError(f"Node {node_path!r} is not an HDA instance")
                if hda_file_path:
                    save_path = resolve_output_path(hou, hda_file_path, _HDA_SUFFIXES)
                else:
                    save_path = defn.libraryFilePath()
                defn.save(save_path)
                return ok({"saved_to": save_path})
        return dispatch(work, label="hda_save")
    except Exception as e:
        return err(e)


def _hda_create(node_paths: list, hda_name: str, hda_label: str,
                hda_file_path: str):
    try:
        def work():
            with hou.undos.group("mcp: create hda"):
                nodes = []
                for p in node_paths:
                    n = hou.node(p)
                    if n is None:
                        raise ValueError(f"Node not found: {p!r}")
                    nodes.append(n)
                safe_path = resolve_output_path(hou, hda_file_path, _HDA_SUFFIXES)
                new_node = nodes[0].createDigitalAsset(
                    hda_name, safe_path, hda_label
                )
                return ok({"hda_name": hda_name,
                           "file": safe_path,
                           "node": new_node.path()})
        return dispatch(work, label="hda_create")
    except Exception as e:
        return err(e)


def _hda_section_get(hda_node_type: str, section_name: str):
    try:
        def work():
            defn = None
            for cat_fn in [hou.sopNodeTypeCategory, hou.objNodeTypeCategory,
                           hou.dopNodeTypeCategory, hou.lopNodeTypeCategory]:
                try:
                    defn = hou.hdaDefinition(cat_fn(), hda_node_type, None)
                    if defn:
                        break
                except Exception:
                    continue
            if defn is None:
                raise ValueError(f"HDA not found: {hda_node_type!r}")
            section = defn.sections().get(section_name)
            if section is None:
                available = list(defn.sections().keys())
                raise ValueError(
                    f"Section {section_name!r} not found. "
                    f"Available: {available}"
                )
            return ok({"section": section_name,
                       "content": section.contents()})
        return dispatch(work, label="hda_section_get")
    except Exception as e:
        return err(e)


def _hda_section_set(hda_node_type: str, section_name: str, content: str):
    try:
        def work():
            with hou.undos.group("mcp: set hda section"):
                defn = None
                for cat_fn in [hou.sopNodeTypeCategory, hou.objNodeTypeCategory,
                               hou.dopNodeTypeCategory, hou.lopNodeTypeCategory]:
                    try:
                        defn = hou.hdaDefinition(cat_fn(), hda_node_type, None)
                        if defn:
                            break
                    except Exception:
                        continue
                if defn is None:
                    raise ValueError(f"HDA not found: {hda_node_type!r}")
                if section_name not in defn.sections():
                    available = list(defn.sections().keys())
                    raise ValueError(
                        f"Section {section_name!r} not found. "
                        f"Available: {available}"
                    )
                defn.sections()[section_name].setContents(content)
                return ok({"section": section_name, "updated": True})
        return dispatch(work, label="hda_section_set")
    except Exception as e:
        return err(e)


def register(app):

    @app.tool("hda_list")
    async def hda_list() -> list:
        """List all installed HDAs with their node type, label, and version."""
        return as_text(_hda_list())

    @app.tool("hda_info")
    async def hda_info(hda_node_type: str) -> list:
        """Get HDA definition info: sections, label, version."""
        return as_text(_hda_info(hda_node_type))

    @app.tool("hda_versions")
    async def hda_versions(hda_node_type: "str | None" = None) -> list:
        """List loaded HDA versions, optionally filtered by node type."""
        return as_text(_hda_versions(hda_node_type))

    @app.tool("hda_install")
    async def hda_install(hda_path: str) -> list:
        """Install an HDA file into the current session."""
        return as_text(_hda_install(hda_path))

    @app.tool("hda_uninstall")
    async def hda_uninstall(hda_node_type: str) -> list:
        """Uninstall an HDA definition from the current session."""
        return as_text(_hda_uninstall(hda_node_type))

    @app.tool("hda_save")
    async def hda_save(node_path: str, hda_file_path: "str | None" = None) -> list:
        """Save the HDA definition of an HDA instance node to disk."""
        return as_text(_hda_save(node_path, hda_file_path))

    @app.tool("hda_create")
    async def hda_create(node_paths: list, hda_name: str,
                          hda_label: str, hda_file_path: str) -> list:
        """Convert nodes into a new HDA. node_paths is a list of node paths to wrap."""
        return as_text(_hda_create(node_paths, hda_name, hda_label, hda_file_path))

    @app.tool("hda_section_get")
    async def hda_section_get(hda_node_type: str, section_name: str) -> list:
        """Get the text content of an HDA section (e.g. 'PythonCook', 'OnLoaded').
        WARNING: Sections like PythonCook, OnLoaded, OnCreated, OnDeleted contain
        Python code that executes when the HDA cooks or is installed."""
        return as_text(_hda_section_get(hda_node_type, section_name))

    @app.tool("hda_section_set")
    async def hda_section_set(hda_node_type: str, section_name: str,
                               content: str) -> list:
        """Set the text content of an HDA section.
        WARNING: Writing to PythonCook, OnLoaded, OnCreated, or OnDeleted injects
        Python code that executes whenever the HDA cooks or is installed. Treat this
        with the same caution as arbitrary code execution."""
        return as_text(_hda_section_set(hda_node_type, section_name, content))
