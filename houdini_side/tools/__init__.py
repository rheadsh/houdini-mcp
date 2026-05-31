from .session import register as register_session
from .nodes import register as register_nodes
from .parameters import register as register_parameters
from .geometry import register as register_geometry
from .transforms import register as register_transforms
from .rendering import register as register_rendering
from .animation import register as register_animation
from .hda import register as register_hda
from .dynamics import register as register_dynamics
from .solaris import register as register_solaris
from .pdg import register as register_pdg
from .takes import register as register_takes
from .vex import register as register_vex
from .utils import register as register_utils

ALL_REGISTERS = [
    register_session, register_nodes, register_parameters,
    register_geometry, register_transforms, register_rendering,
    register_animation, register_hda, register_dynamics,
    register_solaris, register_pdg, register_takes,
    register_vex, register_utils,
]
