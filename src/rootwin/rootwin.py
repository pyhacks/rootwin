import ctypes
import os


dir_name = os.path.split(__file__)[0]
root_interface = None


def redirect_std_files():
    code = b"""
    HANDLE python_stdout_pipe = CreateNamedPipeA("\\\\\\\\.\\\\pipe\\\\rootwin_stdout_loopback",
                     PIPE_ACCESS_DUPLEX,
                     PIPE_TYPE_BYTE,
                     PIPE_UNLIMITED_INSTANCES,
                     10000,
                     10000,
                     NULL,
                     NULL);
    HANDLE python_stderr_pipe = CreateNamedPipeA("\\\\\\\\.\\\\pipe\\\\rootwin_stderr_loopback",
                     PIPE_ACCESS_DUPLEX,
                     PIPE_TYPE_BYTE,
                     PIPE_UNLIMITED_INSTANCES,
                     10000,
                     10000,
                     NULL,
                     NULL);                 
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""std::fstream stdout_redirect = std::fstream("\\\\\\\\.\\\\pipe\\\\rootwin_stdout_loopback", std::ios_base::in | std::ios_base::out);""")
    root_interface.ProcessLine(b"""std::fstream stderr_redirect = std::fstream("\\\\\\\\.\\\\pipe\\\\rootwin_stderr_loopback", std::ios_base::in | std::ios_base::out);""")
    root_interface.ProcessLine(b"HANDLE current_thread = GetCurrentThread();")
    root_interface.ProcessLine(b"HANDLE original_thread;")
    root_interface.ProcessLine(b"DuplicateHandle(GetCurrentProcess(), current_thread, GetCurrentProcess(), &original_thread, NULL, FALSE, DUPLICATE_SAME_ACCESS);")
    code = b"""
    VOID completion_callback(DWORD dwErrorCode, DWORD dwNumberOfBytesTransfered, LPOVERLAPPED lpOverlapped)
    {
        SetEvent(lpOverlapped->hEvent);
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    DWORD python_stdout_write(LPVOID lpParameter)
    {        
        while (true)
        {
            char *str = new char[100];
            memset(str, 0, 100);
            DWORD have_read = 0;           
            ReadFile(python_stdout_pipe, str, 100, &have_read, NULL);         
            PyGILState_STATE state = PyGILState_Ensure();        
            PySys_WriteStdout(str);        
            PyGILState_Release(state);
            delete[] str;
        }
        return 0;
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    DWORD python_stderr_write(LPVOID lpParameter)
    {
        while (true)
        {
            char *str = new char[100];
            memset(str, 0, 100);
            DWORD have_read = 0;           
            ReadFile(python_stderr_pipe, str, 100, &have_read, NULL);         
            PyGILState_STATE state = PyGILState_Ensure();        
            PySys_WriteStderr(str);        
            PyGILState_Release(state);
            delete[] str;
        }
        return 0;
    }
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"HANDLE t1 = CreateThread(NULL, 0, python_stdout_write, NULL, NULL, NULL);")
    root_interface.ProcessLine(b"HANDLE t2 = CreateThread(NULL, 0, python_stderr_write, NULL, NULL, NULL);")
    root_interface.ProcessLine(b"""std::cout.rdbuf(stdout_redirect.rdbuf());""")
    root_interface.ProcessLine(b"""std::cerr.rdbuf(stderr_redirect.rdbuf());""")
    

def init_root():
    global root_interface
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
    code = b"""
    class PyOStream
    {
    public:
        template<typename T>
        PyOStream& operator<<(T var)
        {
            std::stringstream ss;
            ss << var;
            PyGILState_STATE state = PyGILState_Ensure();
            PySys_WriteStdout(ss.str().c_str());
            PyGILState_Release(state);    
            return *this;
        }
    };


    PyOStream pyout;
    """
    root_interface.ProcessLine(code)
    redirect_std_files()
    return root_interface


def init():
    cd = os.getcwd()
    os.chdir(dir_name)  
    init_root()
    os.chdir(cd)


init()
