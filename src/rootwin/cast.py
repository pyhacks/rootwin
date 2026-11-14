import abc

from . import root_interface
from . import interop
from .cpp_world import CppVariable, CppFunction

class BaseCast(abc.ABC):
    @abc.abstractmethod
    def __init__(self):
        self.result_type = None
        self.cast_keyword = None
        
    def __getitem__(self, key):
        if type(key) != str:
            raise TypeError("target type must be given as a str")
        self.result_type = key
        return self

    def __call__(self, cpp_var_or_func):
        if self.result_type is None:
            raise RuntimeError("target type is not set")
        if type(cpp_var_or_func) not in [CppVariable, CppFunction]:
            raise TypeError("Can cast only variables and functions")
        new_name = CppVariable.prefix + str(CppVariable.counter)
        CppVariable.counter += 1
        code = f"auto&& {new_name} = {self.cast_keyword}<{self.result_type}>({cpp_var_or_func.name});"
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        new_name_bytes = bytes(new_name, encoding = "utf-8")
        interop.variables.append(new_name_bytes)
        new_var = CppVariable(new_name)
        return new_var


class StaticCast(BaseCast):
    def __init__(self):
        self.result_type = None
        self.cast_keyword = "static_cast"


class DynamicCast(BaseCast):
    def __init__(self):
        self.result_type = None
        self.cast_keyword = "dynamic_cast"


class ReinterpretCast(BaseCast):
    def __init__(self):
        self.result_type = None
        self.cast_keyword = "reinterpret_cast"


class ConstCast(BaseCast):
    def __init__(self):
        self.result_type = None
        self.cast_keyword = "const_cast"

    
static_cast = StaticCast()
dynamic_cast = DynamicCast()
reinterpret_cast = ReinterpretCast()
const_cast = ConstCast()
            

