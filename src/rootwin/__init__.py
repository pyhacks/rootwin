from .log import log, enable_logging, disable_logging
from . import install
from .rootwin import *


root_interface = None
clang_core = None
std = None
ProcessLine = None

        
def init1():
    global root_interface
    global clang_core
    global std
    global ProcessLine
    dir_name = os.path.split(__file__)[0]
    os.add_dll_directory(dir_name)
    os.add_dll_directory(os.path.join(dir_name, "root", "bin"))  
    root_interface = load_root_interface()
    ProcessLine = root_interface.ProcessLine
    log("[+] root_interface.dll has been loaded")    
    clang_core = ctypes.CDLL("clang_core.dll") 
    log("[+] clang_core.dll has been loaded")
    load_headers(root_interface)
    define_cpp_api(root_interface)    
    redirect_std_files(root_interface)
    std = ctypes.CDLL("std.dll")
    log("[+] std.dll has been loaded")
    if sys.__stdout__ is not None:
        os.system("") # enables rendering ansi escapes and prevents weird shit from occuring when interactive shell is used from cmd instead of IDLE


def init2():
    load_cpp_names()
    log("[+] Updated the C++ names cache")


def fix_dir(func):
    dir_name = os.path.split(__file__)[0]
    def wrapper(*args, **kwargs):
        cd = os.getcwd()
        os.chdir(dir_name)    
        result = func(*args, **kwargs)
        os.chdir(cd)
        return result

    return wrapper


@fix_dir     
def load(): 
    init1()
    global load_cpp_names, cpp_to_int
    global cpp_world, new, delete
    global static_cast, dynamic_cast, reinterpret_cast, const_cast
    from .interop import load_cpp_names, cpp_to_int
    from .cpp_world import cpp_world, new, delete
    from .cast import static_cast, dynamic_cast, reinterpret_cast, const_cast
    init2()

#load() # uncomment if you won't need disable_logging()
