import ctypes
import os


dir_name = os.path.split(__file__)[0]
root_interface = None


def init_root():
    os.add_dll_directory(dir_name)
    os.add_dll_directory(os.path.join(dir_name, "root", "bin"))
    root_interface = ctypes.CDLL("root_interface.dll")
    root_interface.ProcessLine.argtypes = [ctypes.c_char_p]
    root_interface.ProcessLine.restype = None
    root_interface.ProcessLine(b".include python")
    root_interface.ProcessLine(b"""#include \"Python.h\"""")
    code = b"""
template<typename T>
T py_to_pointer(const char *name, bool local = true)
{
    PyGILState_STATE state = PyGILState_Ensure();
    PyObject *locals;
    if (local == true)
    {
        locals = PyEval_GetFrameLocals();
    }
    else
    {
        locals = PyEval_GetFrameGlobals();
    }
    PyObject *pyobject_address = PyDict_GetItemString(locals, name);
    long long address = PyLong_AsLongLong(pyobject_address);
    T obj = reinterpret_cast<T>(address);
    PyGILState_Release(state);
    return obj;
}
"""
    root_interface.ProcessLine(code)    
    return root_interface


def init():
    global root_interface
    cd = os.getcwd()
    os.chdir(dir_name)  
    root_interface = init_root()
    os.chdir(cd)


init()
