from . import install
from .rootwin import root_interface
from .interop import load_cpp_names, cpp_to_int
from .cpp_world import cpp_world, new, delete
from .cast import static_cast, dynamic_cast, reinterpret_cast, const_cast


ProcessLine = root_interface.ProcessLine

load_cpp_names()
