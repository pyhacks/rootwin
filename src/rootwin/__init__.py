from . import install
from .rootwin import *


dir_name = os.path.split(__file__)[0]
root_interface = None
clang_core = None
std = None
log_flag = True


def log(string):
    if log_flag:
        print(string)


def enable_logging():
    cd = os.getcwd()
    os.chdir(dir_name)    
    with open("log_flag.txt", "w") as f:
        f.write("1")
    os.chdir(cd)


def disable_logging():
    cd = os.getcwd()
    os.chdir(dir_name)        
    with open("log_flag.txt", "w") as f:
        f.write("0")
    os.chdir(cd)

        
def init1():
    global root_interface
    global clang_core
    global std
    os.add_dll_directory(dir_name)
    os.add_dll_directory(os.path.join(dir_name, "root", "bin"))  
    root_interface = load_root_interface()
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
    

def init():
    global log_flag
    cd = os.getcwd()
    os.chdir(dir_name)
    with open("log_flag.txt", "r") as f:
        log_flag = f.read()
        log_flag = int(log_flag)
    init1()
    os.chdir(cd)


init()

from .interop import load_cpp_names, cpp_to_int
from .cpp_world import cpp_world, new, delete
from .cast import static_cast, dynamic_cast, reinterpret_cast, const_cast

init2()

ProcessLine = root_interface.ProcessLine
