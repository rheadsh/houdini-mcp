"""DOP simulation tools."""
import hou  # type: ignore[import-untyped]
from houdini_side.dispatcher import dispatch, ok, err
from houdini_side.tools.common import as_text


def _dop_sim_enable(dop_net_path: str, on: bool):
    try:
        def work():
            node = hou.node(dop_net_path)
            if node is None:
                raise ValueError(f"DOP network not found: {dop_net_path!r}")
            p = node.parm("enabled")
            if p:
                p.set(1 if on else 0)
            else:
                hou.setSimulationEnabled(on)
            return ok({"path": dop_net_path, "enabled": on})
        return dispatch(work, label="dop_sim_enable")
    except Exception as e:
        return err(e)


def _dop_sim_reset(dop_net_path: str):
    try:
        def work():
            node = hou.node(dop_net_path)
            if node is None:
                raise ValueError(f"DOP network not found: {dop_net_path!r}")
            p = node.parm("resimulate")
            if p:
                p.pressButton()
            return ok({"reset": dop_net_path})
        return dispatch(work, label="dop_sim_reset")
    except Exception as e:
        return err(e)


def _dop_object_list(dop_net_path: str):
    try:
        def work():
            node = hou.node(dop_net_path)
            if node is None:
                raise ValueError(f"DOP network not found: {dop_net_path!r}")
            sim = node.simulation()
            objects = [{"name": obj.name()} for obj in sim.objects()]
            return ok({"objects": objects, "count": len(objects)})
        return dispatch(work, label="dop_object_list")
    except Exception as e:
        return err(e)


def _dop_object_info(dop_net_path: str, object_name: str):
    try:
        def work():
            node = hou.node(dop_net_path)
            if node is None:
                raise ValueError(f"DOP network not found: {dop_net_path!r}")
            sim = node.simulation()
            obj = sim.findObject(object_name)
            if obj is None:
                raise ValueError(f"DOP object not found: {object_name!r}")
            data_names = [d.name() for d in obj.allData()]
            return ok({"name": object_name, "data": data_names})
        return dispatch(work, label="dop_object_info")
    except Exception as e:
        return err(e)


def _dop_data_get(dop_net_path: str, object_name: str, data_name: str):
    try:
        def work():
            node = hou.node(dop_net_path)
            if node is None:
                raise ValueError(f"DOP network not found: {dop_net_path!r}")
            sim = node.simulation()
            obj = sim.findObject(object_name)
            if obj is None:
                raise ValueError(f"DOP object not found: {object_name!r}")
            data = obj.findData(data_name)
            if data is None:
                raise ValueError(f"DOP data {data_name!r} not found on {object_name!r}")
            return ok({"object": object_name, "data": data_name,
                       "value": str(data)})
        return dispatch(work, label="dop_data_get")
    except Exception as e:
        return err(e)


def register(app):

    @app.tool("dop_sim_enable")
    async def dop_sim_enable(dop_net_path: str, on: bool) -> list:
        """Enable or disable a DOP simulation."""
        return as_text(_dop_sim_enable(dop_net_path, on))

    @app.tool("dop_sim_reset")
    async def dop_sim_reset(dop_net_path: str) -> list:
        """Reset a DOP simulation to frame 1 (presses the resimulate button)."""
        return as_text(_dop_sim_reset(dop_net_path))

    @app.tool("dop_object_list")
    async def dop_object_list(dop_net_path: str) -> list:
        """List all DOP objects in a simulation network."""
        return as_text(_dop_object_list(dop_net_path))

    @app.tool("dop_object_info")
    async def dop_object_info(dop_net_path: str, object_name: str) -> list:
        """Get the DOP data records attached to a simulation object."""
        return as_text(_dop_object_info(dop_net_path, object_name))

    @app.tool("dop_data_get")
    async def dop_data_get(dop_net_path: str, object_name: str, data_name: str) -> list:
        """Get a specific DOP data record from a simulation object."""
        return as_text(_dop_data_get(dop_net_path, object_name, data_name))
