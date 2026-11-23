# rootwin
There are a few ways of embedding C++ into python.
All of them requires [cling](https://root.cern/manual/cling/). 
Unlike what many people believe, there exist a working C++ implementation that is able to execute C++ code by interpreting it. Namely, cling.
Moreover, there is a C++ library called [root](https://root.cern/doc/master/classTCling.html#a4fe8839ae10d4f9d871504d7ebca513b) that accesses this interpreter programmatically.
Additionally, root has python [bindings](https://root.cern/manual/python/#just-in-time-compilation-of-small-strings) which support C++17 but they only work on linux.
Also, there is a seperate library called [cppyy](https://cppyy.readthedocs.io/en/latest/) which works on windows if you manage to win the fight against its broken build system. By the way, it [claims](https://cppyy.readthedocs.io/en/latest/installation.html#c-standard-with-pip) to support C++20 by default, but in practice it only supports C++14 and there is no way of increasing this revision. 
Lastly there is this library, **rootwin**, which works on windows and also supports C++17 and it's not fake. 
Additionally, you can use some techniques which are explained below to get some amount of interoperability.

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
- CppVariable
- CppFunction
- ObjectLikeMacro
- FunctionLikeMacro
- CppType
- CppNamespace
- CppTemplate

<a name="cpp-variable"></a>
_class_ **CppVariable**

Represents a C++ variable, including arrays. Almost all the operators are overloaded.
Operators which don't have a python counterpart are implemented as methods.
You can get the list of names of all the members of the C++ object this CppVariable instance wraps by passing the CppVariable instance to [dir()](https://docs.python.org/3/builtins/functions.html#dir).

CppVariable.**negate**()

Implements C++ negation operator: !

CppVariable.**logical_and**()

Implements C++ logical_and operator: &&

CppVariable.**logical_or**()

Implements C++ logical_or operator: ||

CppVariable.**increment**()

Implements C++ increment operator: ++

CppVariable.**decrement**()

Implements C++ decrement operator: --

CppVariable.**dereference**()

Implements C++ dereference operator: *

CppVariable.**address_of**()

Implements C++ address_of operator: &

CppVariable.**sizeof**()

Implements C++ sizeof operator: sizeof()

CppVariable.**is_builtin_typed**()

Return True if the type of the underlying C++ object is primitive.

CppVariable.**name**

A string storing the C++ name of the C++ variable this CppVariable instance wraps. 

CppVariable.**type_name**

A string storing the C++ type name of the C++ variable this CppVariable instance wraps. 

CppVariable.**value**

Value of the underlying C++ variable. 
Reading it only works with variables with primitive types. 
However, writing to it also works with C++ objects with user defined types.
Even though you can write to it, you won't be able to read from it if the wrapped C++ object has a user defined type.
When writing to it, right hand side of the assignment can be one of 2 things:
- Either a python literal which will be converted to the corresponding C++ literal
- or a CppVariable instance (possibly holding a user defined object).

<a name="cpp-function"></a>
_class_ **CppFunction**

Respresents a C++ function, including methods, templated function instantiations and excluding uninstantiated function templates and function like macros.
Calling an instance of this class will result in a call to the underlying C++ function.
While calling an instance of this class, if types of given arguments are selected from builtin types they will be converted to the corresponding C++ primitive types. 
Otherwise, types of given arguments must be [CppVariable](#cpp-variable).
In that case, each corresponding argument passed to the underlying C++ function will be the C++ variable represented by the [CppVariable](#cpp-variable) instance given during calling this CppFunction instance.
If the C++ function returns something, it will always be forwarded as a [CppVariable](#cpp-variable) instance.

CppFunction.**name**

A string storing the C++ name of the C++ function this CppFunction instance wraps. 

CppFunction.**prototype**

A string storing the prototype of this function.

_class_ **ObjectLikeMacro**

This class inherits [CppVariable](#cpp-variable). 
The reason for that is during construction, value of this macro is assigned to a C++ variable.
This C++ variable is managed by ObjectLikeMacro. 

ObjectLikeMacro.**name**

A string storing the C++ name of the C++ variable this ObjectLikeMacro instance manages.   

ObjectLikeMacro.**type_name**

A string storing the C++ type name of the C++ variable this ObjectLikeMacro instance manages.  

_class_ **FunctionLikeMacro**

Wraps a C++ function-like macro. Unlike ObjectLikeMacro, it doesn't inherit anything.
Calling an instance of this class will result in a call to the underlying C++ macro.
While calling an instance of this class, if types of given arguments are selected from builtin types they will be converted to the corresponding C++ primitive types. 
Otherwise, types of given arguments must be [CppVariable](#cpp-variable).
In that case, each corresponding argument passed to the underlying C++ macro will be the C++ variable represented by the [CppVariable](#cpp-variable) instance given during calling this FunctionLikeMacro instance.
Return value will always be forwarded as a [CppVariable](#cpp-variable) instance.

FunctionLikeMacro.**name**

A string storing the C++ name of the C++ macro this FunctionLikeMacro instance wraps. 

_class_ **CppType**

Represents a C++ type, including fundamental types, classes, structs, enums, unions, typedef'ed types, type aliases, class template instantiations and excluding uninstantiated class templates.
You can get the list of names of all the members of the C++ class this CppType instance wraps by passing the CppType instance to [dir()](https://docs.python.org/3/builtins/functions.html#dir).
You can access static members and inner types via member access operator (.) just like you do for instances.
If the C++ type represented by an instance of this class callable, calling an instance of this class will result in instantiation of the corresponding C++ type.
While calling an instance of this class, if types of given arguments are selected from builtin types they will be converted to the corresponding C++ primitive types. 
Otherwise, types of given arguments must be [CppVariable](#cpp-variable).
In that case, each corresponding argument passed to the underlying C++ type's constructor will be the C++ variable represented by the [CppVariable](#cpp-variable) instance given during calling this CppType instance.
Instantiated C++ object will always be forwarded as a [CppVariable](#cpp-variable) instance.

CppType.**name**

A string storing the C++ name of the C++ type this CppType instance wraps. 

CppType.**sizeof**()

Implements C++ sizeof operator: sizeof()

_class_ **CppNamespace**

Represents a C++ namespace.
You can get the list of names of all the members of the C++ namespace this CppNamespace instance wraps by passing the CppNamespace instance to [dir()](https://docs.python.org/3/builtins/functions.html#dir).

CppNamespace.**name**

A string storing the C++ name of the C++ namespace this CppNamespace instance wraps. 

_class_ **CppTemplate**

Represents a C++ template, including variable templates, function templates and class templates.
Template parameters are specified by subscripting with strings. 
Subscription result is either a CppVariable, CppFunction or a CppType instance. 
Example:
```python
cpp_function1 = rootwin.cpp_world.func_template1["int", "float"]
```
CppTemplate.**name**

A string storing the C++ name of the C++ template this CppTemplate instance wraps. 

<a name="load-cpp-names"></a>
rootwin.**load_cpp_names**()

Update the internal cache used by [rootwin.cpp_world](#cpp-world).

rootwin.**new**(type_str, initializer = None)

This function acts like the new keyword of C++. 
_type_str_ is the type name and if given, _initializer_ must be a tuple storing the arguments. 
Elements of _initalizer_ can either be python literals or [CppVariable](#cpp-variable) instances.
If an element is a python literal, it will be converted to its corresponding C++ literal.
Otherwise [CppVariable](#cpp-variable) object's underlying C++ name will be used as the argument.

rootwin.**delete**(cpp_variable, is_array = False)

This function acts like the delete keyword of C++.
_cpp_variable_ must be a [CppVariable](#cpp-variable) instance whose underlying C++ entity will be deleted.
_is_array_ indicates whether this operation acts like the delete keyword or delete[] keyword of C++.
Since its default value is false, it acts like the delete keyword by default.

rootwin.**static_cast**

rootwin.**dynamic_cast**

rootwin.**reinterpret_cast**

rootwin.**const_cast**

These objects act like the casting keywords of C++. 
Target type is specified by subscripting with strings. Subscription result is the same object. 
Then you can specify the source value by calling that object such as:
```python
rootwin.static_cast["int"](rootwin.cpp_world.var1)
```
Source value must be either a [CppVariable](#cpp-variable) object or a [CppFunction](#cpp-function) object. Literals are not supported.
Return value is always a [CppVariable](#cpp-variable) object.

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

# Manually passing C++ objects to python
High level steps are below:
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
 
