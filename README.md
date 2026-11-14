# rootwin
There are a few ways of embedding C++ into python.
All of them requires [cling](https://root.cern/manual/cling/). 
Unlike what many people believe, there exist a working C++ implementation that is able to execute C++ code by interpreting it. Namely, cling.
Moreover, there is a C++ library called [root](https://root.cern/doc/master/classTCling.html#a4fe8839ae10d4f9d871504d7ebca513b) that accesses this interpreter programmatically.
Additionally, root has python [bindings](https://root.cern/manual/python/#just-in-time-compilation-of-small-strings) which support C++17 but they only work on linux.
Also, there is a seperate library called [cppyy](https://cppyy.readthedocs.io/en/latest/) which works on windows if you manage to win the fight against its broken build system. By the way, it [claims](https://cppyy.readthedocs.io/en/latest/installation.html#c-standard-with-pip) to support C++20 by default, but in practice it only supports C++14 and there is no way of increasing this revision. 
Lastly there is this library, **rootwin**, which works on windows and also supports C++17 and it's not fake. 
However, it's interoperability capabilities are more limited compared to root and cppyy. 
Specifically, C++ symbols you define are not automatically wrapped into python objects and made available to python.
Nonetheless, you can use some techniques which are explained below to get some amount of interoperability.

# Installation
```pip install rootwin```

# Python Api
rootwin.**ProcessLine**(code)

Execute the given C++ code (or cling [metacommand](https://root.cern/manual/cling/#full-list-of-metacommands)). _code_ can be a bytes literal. 
_code_ will be converted to [ctypes.c_char_p](https://docs.python.org/3/library/ctypes.html#ctypes.c_char_p) since this is actually a dll function.
Unlike what the name indicates, _code_ can contain multiple lines. 
The only reason why this name is chose is to emphesize that this function does nothing but calls the upstream C++ root library's ProcessLine() function.

rootwin.**root_interface**

This is the underlying [ctypes.CDLL](https://docs.python.org/3/library/ctypes.html#ctypes.CDLL) instance.
Currently, no functions other than ProcessLine() are exported since the need haven't arised.

rootwin.**cpp_to_int**(name)

_name_ must be a bytes literal representing a C++ variable or function. 
Return value is the address of that C++ entity in the form of an ordinary python int.

<a name="cpp-world"></a>
rootwin.**cpp_world**

An object that proxies C++ names to python. 
You can get the list of all currently cached C++ names by executing:
```python
dir(rootwin.cpp_world)
```
When a name is not found in the internal cache, cache is updated by calling [load_cpp_names()](#load-cpp-names).
If you don't want the overhead of calling this function, you can manually update the caches by modifying these lists:
- rootwin.interop.macros
- rootwin.interop.variables
- rootwin.interop.functions
- rootwin.interop.types
- rootwin.interop.namespaces
- rootwin.interop.templates
- rootwin.interop.names

rootwin.interop.names is the concatenation of all the other lists. 
Whenever you modify one of the above lists, you should also modify rootwin.interop.names.
All of the C++ names are proxied. That is achieved by wrapping them into below python classes:
<a name="cpp-names"></a>
- ObjectLikeMacro
- FunctionLikeMacro
- CppVariable
- CppFunction
- CppType
- CppNamespace
- CppTemplate

<a name="load-cpp-names"></a>
rootwin.**load_cpp_names**()

Update the internal cache used by [rootwin.cpp_world](#cpp-world).

rootwin.**new**(type_str, initializer = None)

This function acts like the new keyword of C++. 
_type_str_ is the type name and if given, _initializer_ must be a tuple storing the arguments. 
Elements of _initalizer_ can either be python literals or [CppVariable](#cpp-names) instances.
If an element is a python literal, it will be converted to its corresponding C++ literal.
Otherwise [CppVariable](#cpp-names) object's underlying C++ name will be used as the argument.

rootwin.**delete**(cpp_variable, is_array = False)

This function acts like the delete keyword of C++.
_cpp_variable_ must be a [CppVariable](#cpp-names) instance whose underlying C++ entity will be deleted.
_is_array_ indicates whether this operation acts like the delete keyword or delete[] keyword of C++.
Since its default value is false, it acts like the delete keyword by default.

# C++ Api
This is the api available to the C++ code executed by rootwin.ProcessLine().

```C++
template<typename T>
T py_to_pointer(const char *name, bool local = true)
```
Convert a python int to a C++ pointer and return the result.
_T_ can be any type that can be given to reinterpret_cast\<target-type\>(expression) as a target type.
_name_ is expected to be the name of a python int. Expected scope of this int is determined by the _local_ argument.
If _local_ is true, name is searched in the local variables of the currently executing python function. 
Otherwise, it is searched in python globals.

PyOStream **pyout**;

An alternative to [std::cout](https://en.cppreference.com/cpp/io/cout). 
The problem is when you use an IDE that hooks [sys.stdout](https://docs.python.org/3/library/sys.html#sys.stdout) (e.g, IDLE) std::cout still writes to the original stdout.
This is from IDLE [docs](https://docs.python.org/3/library/idle.html#running-user-code):
> By default, IDLE runs user code in a separate OS process rather than in the user interface process that runs the shell and editor. In the execution process, it replaces sys.stdin, sys.stdout, and sys.stderr with objects that get input from and send output to the Shell window.

Write operations to original stdout are effectless since the user process' console window is invisible. 
In order to solve this problem, rootwin redirects std::cout and std::cerr to sys.stdout and sys.stderr.
Rootwin achieves this by using named pipes. 
A side effect of that is early return from a stream insertion operation, before the data shows up in the shell window. 
The reason for that is, such an operation completes when the data is sent to the named pipe, but not necessarily after it is read from the named pipe by a worker thread which has been created beforehand.
Data will be printed only after the worker thread reads it and sends it to sys.stdout or sys.stderr.
If you want the stream insertion operation to block until the data is printed to screen, use _pyout_ instead of std::cout.

# Passing C++ objects to python
Unlike cppyy and root libraries, manual work is needed to access C++ objects from python. High level steps are below:
1. Prepare the python world for the next steps by instantiating a [ctypes.c_longlong](https://docs.python.org/3/library/ctypes.html#ctypes.c_longlong). This will be our "out" argument.
2. Take the address of this variable and assign it to another variable
3. Call rootwin.ProcessLine(code) where code is a 2 liner trick which exports the address of any C++ object to python.
4. In the first line, call py_to_pointer<long long*>("p2") where "p2" is the name of the python variable we created in the step 2.
5. Next, dereference the pointer returned by py_to_pointer and assign the address of the C++ object you want to access from python to it.
6. ctypes.c_longlong we created in the first step will be updated by the operation we performed on step 5.
7. Convert the ctypes data type to an ordinary python int by accessing its _value_ attribute.
8. Use [pyptrs](https://github.com/pyhacks/pyptrs) in order to dereference the final int.

Example:
```python
import ctypes
import rootwin
import pyptrs

pointer = ctypes.c_longlong(0)
pointer2 = ctypes.addressof(pointer)
rootwin.ProcessLine(b"int cpp_var = 100;")
rootwin.ProcessLine(b"""long long *pointer2 = py_to_pointer<long long*>("pointer2");""")
rootwin.ProcessLine(b"""*pointer2 = reinterpret_cast<long long>(&cpp_var);""")
cpp_pointer = pyptrs.pointer_to_address(pointer.value, ctype = ctypes.c_int)
cpp_var = pyptrs.dereference(cpp_pointer)
var = cpp_var.value
print(var) # prints 100
```

This is a rather simple example but by applying the same logic, you can also transfer more complex objects to python.
This is possible since pyptrs supports pointers to custom ctypes [structures](https://docs.python.org/3/library/ctypes.html#structures-and-unions).

Another example:
```python
import ctypes
import rootwin
import pyptrs

pointer = ctypes.c_longlong(0)
pointer2 = ctypes.addressof(pointer)
code = b"""
struct A
{
    int a = 10;
    int b = 20;
    int c = 30;
};

A cpp_object;
"""
rootwin.ProcessLine(code)
rootwin.ProcessLine(b"""long long *pointer2 = py_to_pointer<long long*>("pointer2");""")
rootwin.ProcessLine(b"""*pointer2 = reinterpret_cast<long long>(&cpp_object);""")
class A(ctypes.Structure):
    _fields_ = [("a", ctypes.c_int),
                ("b", ctypes.c_int),
                ("c", ctypes.c_int)]
    
cpp_pointer = pyptrs.pointer_to_address(pointer.value, ctype = A)
cpp_object = pyptrs.dereference(cpp_pointer)
b = cpp_object.b
print(b)
```
 
