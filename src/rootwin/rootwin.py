import ctypes
import os
import sys

import pyptrs


def load_root_interface():
    root_interface = ctypes.CDLL("root_interface.dll")
    root_interface.ProcessLine.argtypes = [ctypes.c_char_p]
    root_interface.ProcessLine.restype = None
    return root_interface


def load_headers(root_interface):
    from . import log
    root_interface.ProcessLine(b"""#include "core/metacling/src/TCling.h" """)
    root_interface.ProcessLine(b"""#include "core/metacling/src/TClingClassInfo.h" """)
    log("[+] root headers has been loaded")
    root_interface.ProcessLine(b"""#include "cling/Interpreter/Interpreter.h" """)
    root_interface.ProcessLine(b"""#include "cling/Interpreter/IncrementalParser.h" """)
    log("[+] cling headers has been loaded")
    root_interface.ProcessLine(b"""#include "clang/Frontend/CompilerInstance.h" """)
    root_interface.ProcessLine(b"""#include "clang/AST/Type.h" """)
    root_interface.ProcessLine(b"""#include "clang/Basic/IdentifierTable.h" """)
    root_interface.ProcessLine(b"""#include "clang/Basic/LLVM.h" """)
    root_interface.ProcessLine(b"""#include "clang/AST/Decl.h" """)
    root_interface.ProcessLine(b"""#include "clang/AST/ASTContext.h" """)
    root_interface.ProcessLine(b"""#include "clang/AST/ExternalASTSource.h" """)
    root_interface.ProcessLine(b"""#include "clang/AST/DeclLookups.h" """)
    root_interface.ProcessLine(b"""#include "clang/Lex/Preprocessor.h" """)
    root_interface.ProcessLine(b"""#include "clang/Sema/Sema.h" """)
    log("[+] clang headers has been loaded")
    
    
def define_cpp_api(root_interface):
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
    code = b"""    
    void traverse_object_decls(std::vector<const char*> &object_names, clang::Decl *decl)
    {
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);
        clang::LinkageSpecDecl *linkage_spec_decl = clang::dyn_cast<clang::LinkageSpecDecl>(decl);        
        if (named_decl)
        {
            llvm::StringRef name = named_decl->getName();                
            
            clang::VarDecl *var_decl = clang::dyn_cast<clang::VarDecl>(decl);
            clang::FieldDecl *field_decl = clang::dyn_cast<clang::FieldDecl>(decl);
            clang::UsingShadowDecl  *using_shadow_decl = clang::dyn_cast<clang::UsingShadowDecl>(decl);
            clang::UsingDirectiveDecl *using_directive_decl = clang::dyn_cast<clang::UsingDirectiveDecl>(decl);            
            if (var_decl || field_decl)
            {
                object_names.push_back(name.data());                           
            }
            else if (using_shadow_decl)
            {
                clang::NamedDecl *named_decl2 = using_shadow_decl->getTargetDecl();
                traverse_object_decls(object_names, named_decl2);
            }
            else if (using_directive_decl)
            {
                clang::NamespaceDecl *ns_of_using = using_directive_decl->getNominatedNamespace();              
                for (clang::Decl *decl2 : ns_of_using->noload_decls())                
                {
                    traverse_object_decls(object_names, decl2);
                }         
            }
        }
        else if (linkage_spec_decl)
        {                       
            for (clang::Decl *decl2 : linkage_spec_decl->noload_decls())
            {                                
                traverse_object_decls(object_names, decl2);                
            }        
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""    
    void traverse_function_decls(std::vector<const char*> &func_names, clang::Decl *decl)
    {
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);
        clang::LinkageSpecDecl *linkage_spec_decl = clang::dyn_cast<clang::LinkageSpecDecl>(decl);
        if (named_decl)
        {
            llvm::StringRef name = named_decl->getName();                
            
            clang::FunctionDecl *func_decl = clang::dyn_cast<clang::FunctionDecl>(decl);
            clang::UsingShadowDecl  *using_shadow_decl = clang::dyn_cast<clang::UsingShadowDecl>(decl);
            clang::UsingDirectiveDecl *using_directive_decl = clang::dyn_cast<clang::UsingDirectiveDecl>(decl);            
            if (func_decl)
            {
                func_names.push_back(name.data());
            }
            else if (using_shadow_decl)
            {
                clang::NamedDecl *named_decl2 = using_shadow_decl->getTargetDecl();
                traverse_function_decls(func_names, named_decl2);
            }
            else if (using_directive_decl)
            {
                clang::NamespaceDecl *ns_of_using = using_directive_decl->getNominatedNamespace();              
                for (clang::Decl *decl2 : ns_of_using->noload_decls())                
                {
                    traverse_function_decls(func_names, decl2);
                }         
            }
        }
        else if (linkage_spec_decl)
        {                       
            for (clang::Decl *decl2 : linkage_spec_decl->noload_decls())
            {                                
                traverse_function_decls(func_names, decl2);                
            }        
        }
    }
    """
    root_interface.ProcessLine(code)    
    code = b"""
    void traverse_type_decls(std::vector<const char*> &type_names, clang::Decl *decl)
    {
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);
        clang::LinkageSpecDecl *linkage_spec_decl = clang::dyn_cast<clang::LinkageSpecDecl>(decl);
        if (named_decl)
        {
            llvm::StringRef name = named_decl->getName();                
            
            clang::TypeDecl *type_decl = clang::dyn_cast<clang::TypeDecl>(decl);
            clang::UsingShadowDecl  *using_shadow_decl = clang::dyn_cast<clang::UsingShadowDecl>(decl);
            clang::UsingDirectiveDecl *using_directive_decl = clang::dyn_cast<clang::UsingDirectiveDecl>(decl);            
            if (type_decl)
            {
                type_names.push_back(name.data());
            }
            else if (using_shadow_decl)
            {
                clang::NamedDecl *named_decl2 = using_shadow_decl->getTargetDecl();
                traverse_type_decls(type_names, named_decl2);
            }
            else if (using_directive_decl)
            {
                clang::NamespaceDecl *ns_of_using = using_directive_decl->getNominatedNamespace();            
                for (clang::Decl *decl2 : ns_of_using->noload_decls())
                {
                    traverse_type_decls(type_names, decl2);
                }            
            }
        }
        else if (linkage_spec_decl)
        {
            for (clang::Decl *decl2 : linkage_spec_decl->noload_decls())
            {                                
                traverse_type_decls(type_names, decl2);                
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    void traverse_namespace_decls(std::vector<const char*> &namespace_names, clang::Decl *decl)
    {
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);
        clang::LinkageSpecDecl *linkage_spec_decl = clang::dyn_cast<clang::LinkageSpecDecl>(decl);
        if (named_decl)
        {
            llvm::StringRef name = named_decl->getName();                
            
            clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
            clang::UsingDirectiveDecl *using_directive_decl = clang::dyn_cast<clang::UsingDirectiveDecl>(decl);
            if (ns_decl)
            {
                namespace_names.push_back(name.data());
            }
            else if (using_directive_decl)
            {
                clang::NamespaceDecl *ns_of_using = using_directive_decl->getNominatedNamespace();            
                for (clang::Decl *decl2 : ns_of_using->noload_decls())
                {
                    traverse_namespace_decls(namespace_names, decl2);
                }            
            }
        }
        else if (linkage_spec_decl)
        {
            for (clang::Decl *decl2 : linkage_spec_decl->noload_decls())
            {
                traverse_namespace_decls(namespace_names, decl2);
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    void traverse_template_decls(std::vector<const char*> &template_names, clang::Decl *decl)
    {
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);
        clang::LinkageSpecDecl *linkage_spec_decl = clang::dyn_cast<clang::LinkageSpecDecl>(decl);
        if (named_decl)
        {
            llvm::StringRef name = named_decl->getName();                
            
            clang::TemplateDecl *template_decl = clang::dyn_cast<clang::TemplateDecl>(decl);
            clang::UsingShadowDecl  *using_shadow_decl = clang::dyn_cast<clang::UsingShadowDecl>(decl);
            clang::UsingDirectiveDecl *using_directive_decl = clang::dyn_cast<clang::UsingDirectiveDecl>(decl);
            if (template_decl)
            {
                template_names.push_back(name.data());
            }
            else if (using_shadow_decl)
            {
                clang::NamedDecl *named_decl2 = using_shadow_decl->getTargetDecl();
                traverse_template_decls(template_names, named_decl2);
            }            
            else if (using_directive_decl)
            {
                clang::NamespaceDecl *ns_of_using = using_directive_decl->getNominatedNamespace();            
                for (clang::Decl *decl2 : ns_of_using->noload_decls())
                {
                    traverse_template_decls(template_names, decl2);
                }            
            }
        }
        else if (linkage_spec_decl)
        {
            for (clang::Decl *decl2 : linkage_spec_decl->noload_decls())
            {
                traverse_template_decls(template_names, decl2);
            }
        }
    }
    """
    root_interface.ProcessLine(code)      

   
def redirect_std_files(root_interface):
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
    DWORD python_stdout_write(LPVOID lpParameter)
    {        
        while (true)
        {
            char *str = new char[100];
            memset(str, 0, 100);
            DWORD have_read = 0;           
            ReadFile(python_stdout_pipe, str, 99, &have_read, NULL);         
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
            ReadFile(python_stderr_pipe, str, 99, &have_read, NULL);         
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
    
