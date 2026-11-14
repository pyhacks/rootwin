import ctypes
import pyptrs

from . import root_interface
from . import interop


def value_to_literal(value):
    if type(value) == int:
        value = str(value)
    elif type(value) == str and len(value) == 1:
        value = repr(value)
    elif type(value) == str:
        value = repr(value)
        value = value.replace("\"", "\\\"")
        value = "\"" + value[1:len(value)-1] + "\""
    elif type(value) == bool:
        value = str(value).lower()
    elif type(value) == float:
        value = str(value)
    else:
        raise TypeError("Type of value is not convertible to a C++ literal. Supported python types are: int, str, bool, float")
    return value


def value_to_expr(value):
    try:
        return value_to_literal(value)
    except TypeError:
        if type(value) == CppVariable:
            return value.name
        else:
            raise TypeError(f"Type of value is not convertible to a C++ expression. Supported python types are: int, str, bool, float and {CppVariable}")


def new(type_str, initializer = None):
    new_var_name = CppVariable.prefix + str(CppVariable.counter)
    CppVariable.counter += 1    
    if initializer is not None:
        cpp_args = []
        for arg in initializer:
            cpp_args.append(value_to_expr(arg))
        cpp_args = tuple(cpp_args)
        cpp_args = ", ".join(cpp_args)
        call = f"({cpp_args});"
        operation = "auto {} = new {}" + call
    else:
        operation = "auto {} = new {};"
    code = operation.format(new_var_name, type_str)
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
    if new_var_name_bytes not in interop.names:
        interop.variables.append(new_var_name_bytes)
        interop.names.append(new_var_name_bytes)
    return CppVariable(new_var_name)

    
def delete(cpp_variable, is_array = False):
    if not is_array:
        code = f"delete {cpp_variable.name};"
    else:
        code = f"delete[] {cpp_variable.name};"
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)


class CppVariable:
    prefix = "generated_var"
    counter = 1
       
    def __init__(self, name):
        self.name = name
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.variables:
            raise NameError(f"""Name "{name}" is not a known C++ variable""")        
        code = f"""const char *type_name = typeid({name}).name();"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = interop.cpp_to_int(b"type_name")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        type_name = pyptrs.dereference(p)
        self.type_name = type_name.value.decode()
        self.operation = ""            

    def is_builtin_typed(self):
        code = f"TClass *tclass = TClass::GetClass(typeid({self.name}));"
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = interop.cpp_to_int(b"tclass")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_void_p)
        tclass = pyptrs.dereference(p)
        if tclass.value is None:
            return True
        else:
            return False
        
    @property
    def value(self):
        if not self.is_builtin_typed():
            raise TypeError("Type of this C++ variable is a user defined type")
        root_interface.ProcessLine(b"std::stringstream ss;")
        root_interface.ProcessLine(b"ss.precision(1000);")
        code = f"""ss << {self.name};"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)        
        root_interface.ProcessLine(b"std::string s1 = ss.str();")
        root_interface.ProcessLine(b"""const char *literal_str = s1.c_str();""")
        address = interop.cpp_to_int(b"literal_str")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        literal_str = pyptrs.dereference(p)
        literal_str = literal_str.value.decode()
        
        code = f"bool is_string = std::is_convertible_v<{self.type_name}, const char*>;"
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = interop.cpp_to_int(b"is_string")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_bool)
        is_string = pyptrs.dereference(p)
        if self.type_name == "bool" and literal_str == "0":
            return False
        elif self.type_name == "bool":
            return True
        elif self.type_name in ["char", "signed char", "unsigned char"]:
            return literal_str
        elif is_string:
            return literal_str
        try:
            return int(literal_str)
        except ValueError:
            pass
        try:
            return float(literal_str)
        except ValueError:
            pass
        return literal_str
            
    @value.setter
    def value(self, new_value):
        expr = value_to_expr(new_value)
        code = f"{self.name} = {expr};"
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)

    def do_operation(self, other = None):
        new_var_name = self.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        if other is not None:
            other = value_to_expr(other)
            code = self.operation.format(new_var_name, self.name, other)
        else:
            code = self.operation.format(new_var_name, self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
        if new_var_name_bytes not in interop.names:
            interop.variables.append(new_var_name_bytes)
            interop.names.append(new_var_name_bytes)
        return CppVariable(new_var_name)

    def __dir__(self):
        real_members = object.__dir__(self)
        if not self.is_builtin_typed():
            code = f"""TClass *tclass = TClass::GetClass(typeid({self.name}));"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            if b"tclass" not in interop.names:
                interop.variables.append(b"tclass")
                interop.names.append(b"tclass")
            cpp_members = interop.get_cpp_members(CppVariable("tclass"))
            cpp_members2 = []
            for cpp_member in cpp_members:
                cpp_members2.append(cpp_member.decode())
            members = real_members + cpp_members2
        else:
            members = real_members
        return members

    def __getattr__(self, name):
        if name not in dir(self):
            raise AttributeError(f"Neither 'CppVariable' object nor its underlying C++ object has the attribute '{name}'")
        code = f"""TClass *tclass = TClass::GetClass(typeid({self.name}));"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        tclass = CppVariable("tclass")
        member_vars = interop.get_cpp_member_vars(tclass)
        member_funcs = interop.get_cpp_member_funcs(tclass)
        member_templates = interop.get_cpp_member_templates(tclass)
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes in member_vars:
            self.operation = "auto &&{} = {}." + name + ";"
            return self.do_operation()
        elif name_bytes in member_funcs:
            name = self.name + "." + name
            return CppFunction(name)
        else:
            name = self.name + "." + name
            return CppTemplate(name)

    def __call__(self, *args):
        code = f"""TClass *tclass = TClass::GetClass(typeid({self.name}));"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"""TMethod *method = tclass->GetMethodAllAny("operator()");""")
        root_interface.ProcessLine(b"""const char *return_type = method->GetReturnTypeName();""")
        address = interop.cpp_to_int(b"return_type")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        return_type = pyptrs.dereference(p)
        return_type = return_type.value.decode()
        returns_void = return_type == "void"
        
        cpp_args = []
        for arg in args:
            cpp_args.append(value_to_expr(arg))
        cpp_args = tuple(cpp_args)
        cpp_args = ", ".join(cpp_args)
        call = f"({cpp_args});"        
        if not returns_void:
            self.operation = "auto &&{} = {}" + call
            new_var_name = self.prefix + str(CppVariable.counter)
            CppVariable.counter += 1
            code = self.operation.format(new_var_name, self.name)
        else:
            self.operation = "{}" + call
            code = self.operation.format(self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        if not returns_void:
            new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
            if new_var_name_bytes not in interop.names:
                interop.variables.append(new_var_name_bytes)
                interop.names.append(new_var_name_bytes)
            return CppVariable(new_var_name)

    def __getitem__(self, key):
        self.operation = "auto &&{} = {}[{}];"
        return self.do_operation(key)

    def __setitem__(self, key, value):
        key = value_to_expr(key)
        value = value_to_expr(value)                
        code = f"{self.name}[{key}] = {value};"
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        
    def __add__(self, other):
        self.operation = "auto &&{} = {} + {};"
        return self.do_operation(other)

    def __sub__(self, other):
        self.operation = "auto &&{} = {} - {};"
        return self.do_operation(other)

    def __mul__(self, other):
        self.operation = "auto &&{} = {} * {};"
        return self.do_operation(other)

    def __truediv__(self, other):
        self.operation = "auto &&{} = {} / {};"
        return self.do_operation(other)

    def __mod__(self, other):
        self.operation = "auto &&{} = {} % {};"
        return self.do_operation(other)

    def __xor__(self, other):
        self.operation = "auto &&{} = {} ^ {};"
        return self.do_operation(other)

    def __and__(self, other):
        self.operation = "auto &&{} = {} & {};"
        return self.do_operation(other)

    def __or__(self, other):
        self.operation = "auto &&{} = {} | {};"
        return self.do_operation(other)

    def __lshift__(self, other):
        self.operation = "auto &&{} = {} << {};"
        return self.do_operation(other)

    def __rshift__(self, other):
        self.operation = "auto &&{} = {} >> {};"
        return self.do_operation(other)

    def __radd__(self, other):
        self.operation = "auto &&{} = {} + {};"
        return self.do_operation(other)

    def __rsub__(self, other):
        self.operation = "auto &&{} = {} - {};"
        return self.do_operation(other)

    def __rmul__(self, other):
        self.operation = "auto &&{} = {} * {};"
        return self.do_operation(other)

    def __rtruediv__(self, other):
        self.operation = "auto &&{} = {} / {};"
        return self.do_operation(other)

    def __rmod__(self, other):
        self.operation = "auto &&{} = {} % {};"
        return self.do_operation(other)

    def __rxor__(self, other):
        self.operation = "auto &&{} = {} ^ {};"
        return self.do_operation(other)

    def __rand__(self, other):
        self.operation = "auto &&{} = {} & {};"
        return self.do_operation(other)

    def __ror__(self, other):
        self.operation = "auto &&{} = {} | {};"
        return self.do_operation(other)

    def __rlshift__(self, other):
        self.operation = "auto &&{} = {} << {};"
        return self.do_operation(other)

    def __rrshift__(self, other):
        self.operation = "auto &&{} = {} >> {};"
        return self.do_operation(other)

    def __iadd__(self, other):
        self.operation = "auto &&{} = {} += {};"
        return self.do_operation(other)

    def __isub__(self, other):
        self.operation = "auto &&{} = {} -= {};"
        return self.do_operation(other)

    def __imul__(self, other):
        self.operation = "auto &&{} = {} *= {};"
        return self.do_operation(other)

    def __itruediv__(self, other):
        self.operation = "auto &&{} = {} /= {};"
        return self.do_operation(other)

    def __imod__(self, other):
        self.operation = "auto &&{} = {} %= {};"
        return self.do_operation(other)

    def __ixor__(self, other):
        self.operation = "auto &&{} = {} ^= {};"
        return self.do_operation(other)

    def __iand__(self, other):
        self.operation = "auto &&{} = {} &= {};"
        return self.do_operation(other)

    def __ior__(self, other):
        self.operation = "auto &&{} = {} |= {};"
        return self.do_operation(other)

    def __ilshift__(self, other):
        self.operation = "auto &&{} = {} <<= {};"
        return self.do_operation(other)

    def __irshift__(self, other):
        self.operation = "auto &&{} = {} >>= {};"
        return self.do_operation(other)    

    def __eq__(self, other):
        self.operation = "auto &&{} = {} == {};"
        return self.do_operation(other)

    def __ne__(self, other):
        self.operation = "auto &&{} = {} != {};"
        return self.do_operation(other)

    def __lt__(self, other):
        self.operation = "auto &&{} = {} < {};"
        return self.do_operation(other)

    def __gt__(self, other):
        self.operation = "auto &&{} = {} > {};"
        return self.do_operation(other)

    def __le__(self, other):
        self.operation = "auto &&{} = {} <= {};"
        return self.do_operation(other)

    def __ge__(self, other):
        self.operation = "auto &&{} = {} >= {};"
        return self.do_operation(other)

    def __invert__(self):
        self.operation = "auto &&{} = ~{};"
        return self.do_operation()

    def negate(self):
        self.operation = "auto &&{} = !{};"
        return self.do_operation()

    def logical_and(self, other):
        self.operation = "auto &&{} = {} && {};"
        return self.do_operation(other)        

    def logical_or(self, other):
        self.operation = "auto &&{} = {} || {};"
        return self.do_operation(other)        

    def increment(self):
        self.operation = "auto &&{} = {}++;"
        return self.do_operation()        

    def decrement(self):
        self.operation = "auto &&{} = {}--;"
        return self.do_operation()        

    def dereference(self):
        self.operation = "auto &&{} = *{};"
        return self.do_operation()

    def address_of(self):
        self.operation = "auto &&{} = &{};"
        return self.do_operation()            

    def sizeof(self):
        self.operation = "auto &&{} = sizeof({});"
        return self.do_operation()            
        

class CppFunction:
    def __init__(self, name):
        self.name = name
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.functions and "." not in name and "::" not in name:
            raise NameError(f"""Name "{name}" is not a known C++ function""")
        elif name_bytes not in interop.functions:
            dot_index = name.rfind(".")
            double_colon_index = name.rfind("::")
            biggest_index = max(dot_index, double_colon_index)
            if biggest_index == -1:
                raise NameError(f"""Name "{name}" is not a known C++ function""")
            elif dot_index == -1:
                rightmost_char = "::"
            elif double_colon_index == -1:
                rightmost_char = "."
            elif biggest_index == dot_index:
                rightmost_char = "."
            else:
                rightmost_char = "::"
            if rightmost_char == ".":
                prefix_is_object = True                
            else:
                prefix_is_object = False
            prefix = name.split(rightmost_char)
            func_name = prefix.pop()
            template_name = func_name.split("<")
            template_name = template_name[0]            
            prefix = rightmost_char.join(prefix)
            if prefix_is_object:
                code = f"""TClass *tclass = TClass::GetClass(typeid({prefix}));"""
                code = bytes(code, encoding = "utf-8")
                root_interface.ProcessLine(code)
            else:
                code = f"""TClass *tclass = TClass::GetClass("{prefix}");"""
                code = bytes(code, encoding = "utf-8")
                root_interface.ProcessLine(code)
            if b"tclass" not in interop.names: 
                interop.variables.append(b"tclass")
                interop.names.append(b"tclass")
            tclass = CppVariable("tclass")
            member_funcs = interop.get_cpp_member_funcs(tclass)
            func_name_bytes = bytes(template_name, encoding = "utf-8")
            
            member_templates = interop.get_cpp_member_templates(tclass)
            for member_template in member_templates:
                if func_name_bytes in member_template:
                    break
            else:
                if func_name_bytes not in member_funcs:                
                    raise NameError(f"""Name "{name}" is not a known C++ function""")
            code = f"""TMethod *method = tclass->GetMethodAllAny("{func_name}");"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            root_interface.ProcessLine(b"""const char *prototype = method->GetPrototype();""")
            root_interface.ProcessLine(b"""const char *return_type = method->GetReturnTypeName();""")
            address = interop.cpp_to_int(b"return_type")
            p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
            return_type = pyptrs.dereference(p)
            return_type = return_type.value.decode()
            self.returns_void = return_type == "void"            
        else:
            root_interface.ProcessLine(b"""TCollection *functions = gROOT->GetListOfGlobalFunctions(kFALSE);""")
            code = f"""TObject *tobj = functions->FindObject("{name}");"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            root_interface.ProcessLine(b"""TFunction *function1 = dynamic_cast<TFunction*>(tobj);""")
            root_interface.ProcessLine(b"""const char *prototype = function1->GetPrototype();""")
            root_interface.ProcessLine(b"""const char *return_type = function1->GetReturnTypeName();""")
            address = interop.cpp_to_int(b"return_type")
            p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
            return_type = pyptrs.dereference(p)
            return_type = return_type.value.decode()
            self.returns_void = return_type == "void"            
        address = interop.cpp_to_int(b"prototype")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        prototype = pyptrs.dereference(p)
        self.prototype = prototype.value.decode()

    def __call__(self, *args):
        returns_void = self.returns_void
        cpp_args = []
        for arg in args:
            cpp_args.append(value_to_expr(arg))
        cpp_args = tuple(cpp_args)
        cpp_args = ", ".join(cpp_args)
        call = f"({cpp_args});"        
        if not returns_void:
            self.operation = "auto &&{} = {}" + call
            new_var_name = CppVariable.prefix + str(CppVariable.counter)
            CppVariable.counter += 1
            code = self.operation.format(new_var_name, self.name)
        else:
            self.operation = "{}" + call
            code = self.operation.format(self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        if not returns_void:
            new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
            if new_var_name_bytes not in interop.names:
                interop.variables.append(new_var_name_bytes)
                interop.names.append(new_var_name_bytes)
            return CppVariable(new_var_name)


class ObjectLikeMacro(CppVariable):
    def __init__(self, name):
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.macros:
            raise NameError(f"""Name "{name}" is not a known C++ macro""")        
        
        new_var_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        code = f"""auto &&{new_var_name} = {name};"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        
        self.name = new_var_name
        code = f"""const char *type_name = typeid({name}).name();"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = interop.cpp_to_int(b"type_name")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        type_name = pyptrs.dereference(p)
        self.type_name = type_name.value.decode()
        self.operation = ""            


class FunctionLikeMacro:
    def __init__(self, name):
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.macros:
            raise NameError(f"""Name "{name}" is not a known C++ macro""")
        self.name = name

    def __call__(self, *args):
        cpp_args = []
        for arg in args:
            cpp_args.append(value_to_expr(arg))
        cpp_args = tuple(cpp_args)
        cpp_args = ", ".join(cpp_args)
        call = f"({cpp_args});"        
        self.operation = "auto &&{} = {}" + call
        new_var_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        code = self.operation.format(new_var_name, self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
        if new_var_name_bytes not in interop.names:
            interop.variables.append(new_var_name_bytes)
            interop.names.append(new_var_name_bytes)
        return CppVariable(new_var_name)        


def handle_macro(name):
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"clang::Preprocessor &preprocessor = compiler_instance->getPreprocessor();")
    code = f"""clang::IdentifierInfo *identifier_info = Preprocessor_getIdentifierInfo(&preprocessor, "{name}");"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)    
    root_interface.ProcessLine(b"""clang::MacroInfo* macro_info = Preprocessor_getMacroInfo(&preprocessor, identifier_info);""")
    root_interface.ProcessLine(b"""bool is_func_like = macro_info->isFunctionLike();""")
    address = interop.cpp_to_int(b"is_func_like")
    p = pyptrs.pointer_to_address(address, ctype = ctypes.c_bool)
    is_func_like = pyptrs.dereference(p)
    is_func_like = is_func_like.value
    if is_func_like:
        return FunctionLikeMacro(name)
    else:
        return ObjectLikeMacro(name)        


class CppType:
    def __init__(self, name):
        self.name = name
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.types and "::" not in name:
            raise NameError(f"""Name "{name}" is not a known C++ type""")
        elif name_bytes not in interop.types:
            double_colon_index = name.rfind("::")
            if double_colon_index == -1:
                raise NameError(f"""Name "{name}" is not a known C++ type""")
            prefix_is_object = False
            prefix = name.split("::")
            type_name = prefix.pop()
            prefix = "::".join(prefix)
            code = f"""TClass *tclass = TClass::GetClass("{prefix}");"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            if b"tclass" not in interop.names:
                interop.variables.append(b"tclass")
                interop.names.append(b"tclass")
            tclass = CppVariable("tclass")
            member_types = interop.get_partial_cpp_scope(tclass, name_type = "type")
            type_name_bytes = bytes(type_name, encoding = "utf-8")
            if type_name_bytes not in member_types:
                raise NameError(f"""Name "{name}" is not a known C++ type""")                  

    def __dir__(self):
        real_members = object.__dir__(self)
        code = f"""TClass *tclass = TClass::GetClass("{self.name}");"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        if b"tclass" not in interop.names:
            interop.variables.append(b"tclass")
            interop.names.append(b"tclass")
        tclass = CppVariable("tclass")
        cpp_members = interop.get_cpp_class_scope(tclass)
        cpp_members2 = []
        for cpp_member in cpp_members:
            cpp_members2.append(cpp_member.decode())
        members = real_members + cpp_members2
        return members

    def do_operation(self, other = None):
        new_var_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        if other is not None:
            other = value_to_expr(other)
            code = self.operation.format(new_var_name, self.name, other)
        else:
            code = self.operation.format(new_var_name, self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
        if new_var_name_bytes not in interop.names:
            interop.variables.append(new_var_name_bytes)
            interop.names.append(new_var_name_bytes)
        return CppVariable(new_var_name)

    def __getattr__(self, name):
        if name not in dir(self):
            raise AttributeError(f"'CppType' object has no attribute '{name}' and its underlying C++ type can't be used to access this name.")
        code = f"""TClass *tclass = TClass::GetClass("{self.name}");"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        tclass = CppVariable("tclass")
        member_vars = interop.get_cpp_member_vars(tclass, static = True)
        member_funcs = interop.get_cpp_member_funcs(tclass, static = True)
        member_types = interop.get_partial_cpp_scope(tclass, name_type = "type")
        member_namespaces = interop.get_partial_cpp_scope(tclass, name_type = "namespace")
        member_templates1 = interop.get_partial_cpp_scope(tclass, name_type = "template")
        member_templates2 = interop.get_cpp_member_templates(tclass, static = False)
        for member_template in member_templates2:
            member_templates1.remove(member_template)
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes in member_vars:
            self.operation = "auto &&{} = {}::" + name + ";"
            return self.do_operation()
        elif name_bytes in member_funcs:
            name = self.name + "::" + name
            return CppFunction(name)
        elif name_bytes in member_types:
            name = self.name + "::" + name
            return CppType(name)
        elif name_bytes in member_namespaces:
            name = self.name + "::" + name
            return CppNamespace(name)
        else:
            name = self.name + "::" + name
            return CppTemplate(name)    

    def __call__(self, *args):
        cpp_args = []
        for arg in args:
            cpp_args.append(value_to_expr(arg))
        cpp_args = tuple(cpp_args)
        cpp_args = ", ".join(cpp_args)
        call = f"({cpp_args});"        
        self.operation = "auto &&{} = {}" + call
        new_var_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        code = self.operation.format(new_var_name, self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
        if new_var_name_bytes not in interop.names:
            interop.variables.append(new_var_name_bytes)
            interop.names.append(new_var_name_bytes)
        return CppVariable(new_var_name)

    def sizeof(self):
        self.operation = "auto &&{} = sizeof({});"
        return self.do_operation()    


class CppNamespace:
    def __init__(self, name):
        self.name = name
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.namespaces and "::" not in name:
            raise NameError(f"""Name "{name}" is not a known C++ namespace""")
        elif name_bytes not in interop.namespaces:
            double_colon_index = name.rfind("::")
            if double_colon_index == -1:
                raise NameError(f"""Name "{name}" is not a known C++ namespace""")
            prefix_is_object = False
            prefix = name.split("::")
            namespace_name = prefix.pop()
            prefix = "::".join(prefix)
            code = f"""TClass *tclass = TClass::GetClass("{prefix}");"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            if b"tclass" not in interop.names:
                interop.variables.append(b"tclass")
                interop.names.append(b"tclass")
            tclass = CppVariable("tclass")
            member_namespaces = interop.get_partial_cpp_scope(tclass, name_type = "namespace")
            namespace_name_bytes = bytes(namespace_name, encoding = "utf-8")
            if namespace_name_bytes not in member_namespaces:
                raise NameError(f"""Name "{name}" is not a known C++ namespace""")

    def __dir__(self):
        real_members = object.__dir__(self)
        code = f"""TClass *tclass = TClass::GetClass("{self.name}");"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        if b"tclass" not in interop.names:
            interop.variables.append(b"tclass")
            interop.names.append(b"tclass")
        tclass = CppVariable("tclass")
        cpp_members = interop.get_cpp_namespace_scope(tclass)
        cpp_members2 = []
        for cpp_member in cpp_members:
            cpp_members2.append(cpp_member.decode())
        members = real_members + cpp_members2
        return members            

    def do_operation(self, other = None):
        new_var_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        if other is not None:
            other = value_to_expr(other)
            code = self.operation.format(new_var_name, self.name, other)
        else:
            code = self.operation.format(new_var_name, self.name)
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_var_name_bytes = bytes(new_var_name, encoding = "utf-8")
        if new_var_name_bytes not in interop.names:
            interop.variables.append(new_var_name_bytes)
            interop.names.append(new_var_name_bytes)
        return CppVariable(new_var_name)

    def __getattr__(self, name):
        if name not in dir(self):
            raise AttributeError(f"Neither 'CppNamespace' object nor its underlying C++ namespace contains the name '{name}'")
        code = f"""TClass *tclass = TClass::GetClass("{self.name}");"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        tclass = CppVariable("tclass")
        member_vars = interop.get_partial_cpp_scope(tclass, name_type = "variable")
        member_funcs = interop.get_partial_cpp_scope(tclass, name_type = "function")
        member_types = interop.get_partial_cpp_scope(tclass, name_type = "type")
        member_namespaces = interop.get_partial_cpp_scope(tclass, name_type = "namespace")
        member_templates = interop.get_partial_cpp_scope(tclass, name_type = "template")
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes in member_vars:
            self.operation = "auto &&{} = {}::" + name + ";"
            return self.do_operation()
        elif name_bytes in member_funcs:
            name = self.name + "::" + name
            return CppFunction(name)
        elif name_bytes in member_types:
            name = self.name + "::" + name
            return CppType(name)
        elif name_bytes in member_namespaces:
            name = self.name + "::" + name
            return CppNamespace(name)
        else:
            name = self.name + "::" + name
            return CppTemplate(name)    


class CppTemplate:
    def __init__(self, name):
        self.name = name
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.templates and "." not in name and "::" not in name:
            raise NameError(f"""Name "{name}" is not a known C++ template""")
        elif name_bytes not in interop.templates:
            dot_index = name.rfind(".")
            double_colon_index = name.rfind("::")
            biggest_index = max(dot_index, double_colon_index)
            if biggest_index == -1:
                raise NameError(f"""Name "{name}" is not a known C++ template""")
            elif dot_index == -1:
                rightmost_char = "::"
            elif double_colon_index == -1:
                rightmost_char = "."
            elif biggest_index == dot_index:
                rightmost_char = "."
            else:
                rightmost_char = "::"
            if rightmost_char == ".":
                prefix_is_object = True                
            else:
                prefix_is_object = False
            prefix = name.split(rightmost_char)
            template_name = prefix.pop()
            prefix = rightmost_char.join(prefix)
            if prefix_is_object:
                code = f"""TClass *tclass = TClass::GetClass(typeid({prefix}));"""
                code = bytes(code, encoding = "utf-8")
                root_interface.ProcessLine(code)
            else:
                code = f"""TClass *tclass = TClass::GetClass("{prefix}");"""
                code = bytes(code, encoding = "utf-8")
                root_interface.ProcessLine(code)
            if b"tclass" not in interop.names:
                interop.variables.append(b"tclass")
                interop.names.append(b"tclass")
            tclass = CppVariable("tclass")
            member_templates1 = interop.get_cpp_member_templates(tclass)
            if not prefix_is_object:
                member_templates1 = interop.get_cpp_member_templates(tclass, static = False)
                member_templates2 = interop.get_partial_cpp_scope(tclass, name_type = "template")
                for member_template in member_templates1:
                    if member_template in member_templates2:
                        member_templates2.remove(member_template)
            else:
                member_templates2 = member_templates1   
            template_name_bytes = bytes(template_name, encoding = "utf-8")
            if template_name_bytes not in member_templates2:            
                raise NameError(f"""Name "{name}" is not a known C++ template""")
            self.is_global = False
        else:
            self.is_global = True

    def __getitem__(self, args):
        if type(args) == str:
            instantiation = f"{self.name}<{args}>"
        else:
            args_str = ", ".join(args)
            instantiation = f"{self.name}<{args_str}>"
        instantiation_bytes = bytes(instantiation, encoding = "utf-8")

        code = f"""TClass *tclass = TClass::GetClass("{instantiation}");"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = interop.cpp_to_int(b"tclass")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_void_p)
        tclass = pyptrs.dereference(p)
        
        if self.is_global:            
            code = f"""TFunctionTemplate *function_template = gROOT->GetFunctionTemplate("{instantiation}");"""
            code = bytes(code, encoding = "utf-8")
            root_interface.ProcessLine(code)
            address = interop.cpp_to_int(b"function_template")
            p = pyptrs.pointer_to_address(address, ctype = ctypes.c_void_p)
            function_template = pyptrs.dereference(p)
            
            if tclass.value is not None:
                if instantiation_bytes not in interop.names:
                    interop.types.append(instantiation_bytes)
                    interop.names.append(instantiation_bytes)
                return CppType(instantiation)
            elif function_template.value is not None:
                if instantiation_bytes not in interop.names:
                    interop.functions.append(instantiation_bytes)
                    interop.names.append(instantiation_bytes)                
                return CppFunction(instantiation)        
            else:
                if instantiation_bytes not in interop.names:
                    interop.variables.append(instantiation_bytes)
                    interop.names.append(instantiation_bytes)                                
                return CppVariable(instantiation)
        elif tclass.value is not None:
            if instantiation_bytes not in interop.names:
                interop.types.append(instantiation_bytes)
                interop.names.append(instantiation_bytes)
            return CppType(instantiation)            
        else:
            return CppFunction(instantiation)


class CppWorld:
    def __dir__(self):
        return list(interop.names)

    def __getattr__(self, name):
        name_bytes = bytes(name, encoding = "utf-8")
        if name_bytes not in interop.names:
            code = name_bytes + b";"
            root_interface.ProcessLine(code)
            interop.load_cpp_names()
            if name_bytes not in interop.names:
                raise NameError(f"""Name "{name}" is not a known C++ name""")
        if name_bytes in interop.macros:
            return handle_macro(name)
        elif name_bytes in interop.variables:
            return CppVariable(name)
        elif name_bytes in interop.functions:
            return CppFunction(name)
        elif name_bytes in interop.types:
            return CppType(name)
        elif name_bytes in interop.namespaces:
            return CppNamespace(name)
        elif name_bytes in interop.templates:
            return CppTemplate(name)


cpp_world = CppWorld()
