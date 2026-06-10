"""Solaris/USD LOP tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import resolve_output_path, as_text, as_list

_USD_SUFFIXES = (".usd", ".usda", ".usdc", ".usdz")

try:
    from pxr import Usd, Sdf  # type: ignore[import-untyped]
    _PXR_AVAILABLE = True
except ImportError:
    Usd = None  # type: ignore[assignment]
    Sdf = None  # type: ignore[assignment]
    _PXR_AVAILABLE = False


def _require_pxr():
    if not _PXR_AVAILABLE:
        raise RuntimeError(
            "pxr (USD) is not available in this Python environment. "
            "Solaris tools require Houdini's bundled Python with USD support."
        )


def _usd_path(value):
    try:
        return str(value.path)
    except Exception:
        try:
            return str(value.GetPath())
        except Exception:
            return str(value)


def _get_lop_stage(lop_path: str):
    node = hou.node(lop_path)
    if node is None:
        raise ValueError(f"LOP node not found: {lop_path!r}")
    stage = node.stage()
    if stage is None:
        raise ValueError(f"No USD stage on {lop_path!r}")
    return node, stage


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


def _lop_layer_stack(lop_path: str):
    try:
        _require_pxr()
        def work():
            _, stage = _get_lop_stage(lop_path)
            layers = []
            get_layers = getattr(stage, "GetLayerStack", None)
            if not callable(get_layers):
                get_layers = getattr(stage, "GetUsedLayers", None)
            if callable(get_layers):
                raw_layers = get_layers()
                for layer in as_list(raw_layers):
                    layers.append({
                        "identifier": getattr(layer, "identifier", ""),
                        "real_path": getattr(layer, "realPath", ""),
                        "anonymous": bool(getattr(layer, "anonymous", False)),
                        "dirty": bool(getattr(layer, "dirty", False)),
                    })
            else:
                root_layer = getattr(stage, "GetRootLayer", lambda: None)()
                if root_layer is not None:
                    layers.append({
                        "identifier": getattr(root_layer, "identifier", ""),
                        "real_path": getattr(root_layer, "realPath", ""),
                        "anonymous": bool(getattr(root_layer, "anonymous", False)),
                        "dirty": bool(getattr(root_layer, "dirty", False)),
                    })
            return ok({"path": lop_path, "layers": layers, "count": len(layers)})
        return dispatch(work, label="lop_layer_stack")
    except Exception as e:
        return err(e)


def _lop_prim_relationships(lop_path: str, prim_path: str):
    try:
        _require_pxr()
        def work():
            _, stage = _get_lop_stage(lop_path)
            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise ValueError(f"USD prim not found: {prim_path!r}")
            relationships = []
            for rel in prim.GetRelationships():
                targets = []
                get_targets = getattr(rel, "GetTargets", None)
                if callable(get_targets):
                    raw_targets = get_targets()
                    targets = [_usd_path(t) for t in as_list(raw_targets)]
                relationships.append({
                    "name": rel.GetName(),
                    "targets": targets,
                })
            return ok({
                "prim_path": prim_path,
                "relationships": relationships,
                "count": len(relationships),
            })
        return dispatch(work, label="lop_prim_relationships")
    except Exception as e:
        return err(e)


def _lop_material_bindings(lop_path: str, prim_path: str = "/"):
    try:
        _require_pxr()
        def work():
            _, stage = _get_lop_stage(lop_path)
            root = stage.GetPrimAtPath(prim_path)
            if not root.IsValid():
                raise ValueError(f"USD prim not found: {prim_path!r}")
            try:
                from pxr import UsdShade  # type: ignore[import-untyped]
                material_binding_api = UsdShade
            except Exception:
                material_binding_api = None
            if material_binding_api is None or not hasattr(material_binding_api, "MaterialBindingAPI"):
                return ok({
                    "prim_path": prim_path,
                    "bindings": [],
                    "count": 0,
                    "note": "UsdShade.MaterialBindingAPI not available",
                })

            bindings = []
            if Usd is None:
                raise RuntimeError("pxr.Usd is not available")
            for prim in Usd.PrimRange(root):
                try:
                    api = material_binding_api.MaterialBindingAPI(prim)
                    material, relationship = api.ComputeBoundMaterial()
                except Exception:
                    continue
                if not material:
                    continue
                material_path = ""
                try:
                    material_path = _usd_path(material.GetPrim())
                except Exception:
                    material_path = _usd_path(material)
                bindings.append({
                    "prim_path": _usd_path(prim),
                    "material_path": material_path,
                    "relationship": getattr(relationship, "GetName", lambda: "")(),
                })
            return ok({"prim_path": prim_path, "bindings": bindings, "count": len(bindings)})
        return dispatch(work, label="lop_material_bindings")
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
            safe_path = resolve_output_path(hou, file_path, _USD_SUFFIXES)
            stage.Export(safe_path)
            return ok({"saved_to": safe_path})
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
        _require_pxr()  # loadMasks() requires USD-capable Houdini
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

    @app.tool("lop_stage_info")
    async def lop_stage_info(lop_path: str) -> list:
        """Get USD stage info: root prim paths and up-axis. Requires USD (pxr)."""
        return as_text(_lop_stage_info(lop_path))

    @app.tool("lop_prim_list")
    async def lop_prim_list(lop_path: str, prim_path: str = "/") -> list:
        """List children of a USD prim in the stage."""
        return as_text(_lop_prim_list(lop_path, prim_path))

    @app.tool("lop_layer_stack")
    async def lop_layer_stack(lop_path: str) -> list:
        """List USD layers used by a LOP stage. Requires USD (pxr)."""
        return as_text(_lop_layer_stack(lop_path))

    @app.tool("lop_prim_relationships")
    async def lop_prim_relationships(lop_path: str, prim_path: str) -> list:
        """List USD relationships and target paths for a prim."""
        return as_text(_lop_prim_relationships(lop_path, prim_path))

    @app.tool("lop_material_bindings")
    async def lop_material_bindings(lop_path: str, prim_path: str = "/") -> list:
        """List computed material bindings below a USD prim."""
        return as_text(_lop_material_bindings(lop_path, prim_path))

    @app.tool("lop_prim_info")
    async def lop_prim_info(lop_path: str, prim_path: str) -> list:
        """Get USD prim type, attributes, and variant sets."""
        return as_text(_lop_prim_info(lop_path, prim_path))

    @app.tool("lop_save_usd")
    async def lop_save_usd(lop_path: str, file_path: str) -> list:
        """Export the USD stage from a LOP node to a .usd/.usda/.usdc file."""
        return as_text(_lop_save_usd(lop_path, file_path))

    @app.tool("lop_variant_set")
    async def lop_variant_set(lop_path: str, prim_path: str,
                               varset: str, variant: str) -> list:
        """Set a variant selection on a USD prim."""
        return as_text(_lop_variant_set(lop_path, prim_path, varset, variant))

    @app.tool("lop_load_masks")
    async def lop_load_masks(lop_path: str) -> list:
        """Get stage load mask configuration from a LOP node."""
        return as_text(_lop_load_masks(lop_path))
