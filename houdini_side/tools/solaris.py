"""Solaris/USD LOP tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err

try:
    from pxr import Usd, Sdf  # type: ignore[import-untyped]
    _PXR_AVAILABLE = True
except ImportError:
    _PXR_AVAILABLE = False


def _require_pxr():
    if not _PXR_AVAILABLE:
        raise RuntimeError(
            "pxr (USD) is not available in this Python environment. "
            "Solaris tools require Houdini's bundled Python with USD support."
        )


def _lop_stage_info(lop_path: str):
    try:
        _require_pxr()
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            stage = node.stage()
            if stage is None:
                raise ValueError(f"No USD stage available on {lop_path!r}. Cook the node first.")
            root = stage.GetPseudoRoot()
            children = [str(c.GetPath()) for c in root.GetAllChildren()]
            return ok({
                "path": lop_path,
                "root_prims": children[:50],
                "up_axis": stage.GetMetadata("upAxis") or "Y",
            })
        return dispatch(work, label="lop_stage_info")
    except Exception as e:
        return err(e)


def _lop_prim_list(lop_path: str, prim_path: str = "/"):
    try:
        _require_pxr()
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            stage = node.stage()
            if stage is None:
                raise ValueError(f"No USD stage on {lop_path!r}")
            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise ValueError(f"USD prim not found at {prim_path!r}")
            children = [str(c.GetPath()) for c in prim.GetAllChildren()]
            return ok({"prim_path": prim_path,
                       "children": children,
                       "count": len(children)})
        return dispatch(work, label="lop_prim_list")
    except Exception as e:
        return err(e)


def _lop_prim_info(lop_path: str, prim_path: str):
    try:
        _require_pxr()
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            stage = node.stage()
            if stage is None:
                raise ValueError(f"No USD stage on {lop_path!r}")
            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise ValueError(f"USD prim not found at {prim_path!r}")
            attrs = {a.GetName(): str(a.Get()) for a in prim.GetAttributes()}
            varsets = {}
            for vs in prim.GetVariantSets().GetNames():
                varsets[vs] = prim.GetVariantSets().GetVariantSet(vs).GetVariantSelection()
            return ok({
                "prim_path": prim_path,
                "type_name": prim.GetTypeName(),
                "attributes": attrs,
                "variant_sets": varsets,
            })
        return dispatch(work, label="lop_prim_info")
    except Exception as e:
        return err(e)


def _lop_save_usd(lop_path: str, file_path: str):
    try:
        _require_pxr()
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            stage = node.stage()
            if stage is None:
                raise ValueError(f"No USD stage on {lop_path!r}")
            stage.Export(file_path)
            return ok({"saved_to": file_path})
        return dispatch(work, label="lop_save_usd")
    except Exception as e:
        return err(e)


def _lop_variant_set(lop_path: str, prim_path: str,
                     varset: str, variant: str):
    try:
        _require_pxr()
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            stage = node.stage()
            if stage is None:
                raise ValueError(f"No USD stage on {lop_path!r}")
            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise ValueError(f"USD prim not found: {prim_path!r}")
            vs = prim.GetVariantSets().GetVariantSet(varset)
            vs.SetVariantSelection(variant)
            return ok({"prim_path": prim_path,
                       "varset": varset, "variant": variant})
        return dispatch(work, label="lop_variant_set")
    except Exception as e:
        return err(e)


def _lop_load_masks(lop_path: str):
    try:
        def work():
            node = hou.node(lop_path)
            if node is None:
                raise ValueError(f"LOP node not found: {lop_path!r}")
            masks = node.loadMasks()
            return ok({"path": lop_path, "masks": str(masks)})
        return dispatch(work, label="lop_load_masks")
    except Exception as e:
        return err(e)


def register(app):
    import json

    @app.tool("lop_stage_info")
    async def lop_stage_info(lop_path: str) -> list:
        """Get USD stage info: root prim paths and up-axis. Requires USD (pxr)."""
        return [{"type": "text", "text": json.dumps(_lop_stage_info(lop_path))}]

    @app.tool("lop_prim_list")
    async def lop_prim_list(lop_path: str, prim_path: str = "/") -> list:
        """List children of a USD prim in the stage."""
        return [{"type": "text", "text": json.dumps(_lop_prim_list(lop_path, prim_path))}]

    @app.tool("lop_prim_info")
    async def lop_prim_info(lop_path: str, prim_path: str) -> list:
        """Get USD prim type, attributes, and variant sets."""
        return [{"type": "text", "text": json.dumps(_lop_prim_info(lop_path, prim_path))}]

    @app.tool("lop_save_usd")
    async def lop_save_usd(lop_path: str, file_path: str) -> list:
        """Export the USD stage from a LOP node to a .usd/.usda/.usdc file."""
        return [{"type": "text", "text": json.dumps(_lop_save_usd(lop_path, file_path))}]

    @app.tool("lop_variant_set")
    async def lop_variant_set(lop_path: str, prim_path: str,
                               varset: str, variant: str) -> list:
        """Set a variant selection on a USD prim."""
        return [{"type": "text", "text": json.dumps(
            _lop_variant_set(lop_path, prim_path, varset, variant)
        )}]

    @app.tool("lop_load_masks")
    async def lop_load_masks(lop_path: str) -> list:
        """Get stage load mask configuration from a LOP node."""
        return [{"type": "text", "text": json.dumps(_lop_load_masks(lop_path))}]
