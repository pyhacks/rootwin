import ctypes
import pyptrs

from . import root_interface


macros = []
variables = []
functions = []
types = []
namespaces = []
templates = []
names = []


def cpp_to_int(name):
    if type(name) != bytes:
        raise TypeError("name must be a bytes")
    pointer = ctypes.c_longlong(0)
    pointer2 = ctypes.addressof(pointer)
    root_interface.ProcessLine(b"""long long *pointer2 = py_to_pointer<long long*>("pointer2");""")
    root_interface.ProcessLine(b"*pointer2 = reinterpret_cast<long long>(&" + name + b");")
    return pointer.value


def vector_to_list(data_address, size_address):
    size_pointer = pyptrs.pointer_to_address(size_address, ctype = ctypes.c_size_t)
    size = pyptrs.dereference(size_pointer)
    size = size.value
    array_ptr_type = ctypes.POINTER(ctypes.c_char_p * size)
    data_pointer = pyptrs.pointer_to_address(data_address, ctype = array_ptr_type)
    data = pyptrs.dereference(data_pointer).contents
    data = data[:]
    data = list(set(data))
    return data


def get_cpp_macros():
    global macros
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"clang::Preprocessor &preprocessor = compiler_instance->getPreprocessor();") 
    root_interface.ProcessLine(b"std::vector<const char*> global_macros;")
    code = b"""
    for (auto &bucket : preprocessor.macros(true))
    {
        global_macros.push_back(bucket.first->getName().data());
    }    
    """   
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"size_t global_macros_len = global_macros.size();")
    root_interface.ProcessLine(b"const char **global_macros_buffer = global_macros.data();")
    size_address = cpp_to_int(b"global_macros_len")
    data_address = cpp_to_int(b"global_macros_buffer")
    data = vector_to_list(data_address, size_address)
    macros[:] = data
    return list(macros)


def get_cpp_vars():
    global variables
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* global_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(sema.CurContext, *global_decls);")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> all_decls;")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> outer_decls;")    
    root_interface.ProcessLine(b"std::vector<const char*> global_vars;")
    code = b"""
    for (int i = 0; i < global_decls->size(); i++)  
    {
        clang::Decl* decl = (*global_decls)[i];           
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::VarDecl *var_decl = clang::dyn_cast<clang::VarDecl>(decl2);
                        clang::FieldDecl *field_decl = clang::dyn_cast<clang::FieldDecl>(decl2);
                        if (var_decl || field_decl)
                        {
                            global_vars.push_back(name2.data());                           
                        }                            
                    }
                }
            }
            else
            {            
                traverse_object_decls(global_vars, decl);                
            }
        }
        else
        {
            traverse_object_decls(global_vars, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {      
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::VarDecl *var_decl = clang::dyn_cast<clang::VarDecl>(decl2);
                        clang::FieldDecl *field_decl = clang::dyn_cast<clang::FieldDecl>(decl2);
                        if (var_decl || field_decl)
                        {                        
                            global_vars.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_object_decls(global_vars, decl);                
            }
        }
        else
        {
            traverse_object_decls(global_vars, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""external_sema_source->completeVisibleDeclsMap(sema.CurContext);""")    
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_object_decls(global_vars, named_decl);
                    }
                }
            }
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (int i = 0; i < global_decls->size(); i++) 
    {
        clang::Decl* decl = (*global_decls)[i]; 
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_object_decls(global_vars, named_decl);
                    }
                }
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : sema.CurContext->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_object_decls(global_vars, named_decl);
        }
    }
    """
    root_interface.ProcessLine(code)           
    root_interface.ProcessLine(b"size_t global_vars_len = global_vars.size();")
    root_interface.ProcessLine(b"const char **global_vars_buffer = global_vars.data();")
    size_address = cpp_to_int(b"global_vars_len")
    data_address = cpp_to_int(b"global_vars_buffer")
    data = vector_to_list(data_address, size_address)
    variables[:] = data
    return list(variables)


def get_cpp_functions():
    global functions
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* global_decls = new clang::SmallVector<clang::Decl*>();")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(sema.CurContext, *global_decls);")    
    root_interface.ProcessLine(b"std::vector<clang::Decl*> all_decls;")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> outer_decls;")    
    root_interface.ProcessLine(b"std::vector<const char*> global_functions;")    
    code = b"""
    for (int i = 0; i < global_decls->size(); i++)  
    {
        clang::Decl* decl = (*global_decls)[i];           
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::FunctionDecl *func_decl = clang::dyn_cast<clang::FunctionDecl>(decl2);
                        if (func_decl)
                        {                        
                            global_functions.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_function_decls(global_functions, decl);                
            }
        }
        else
        {
            traverse_function_decls(global_functions, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)    
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {      
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::FunctionDecl *func_decl = clang::dyn_cast<clang::FunctionDecl>(decl2);
                        if (func_decl)
                        {                        
                            global_functions.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_function_decls(global_functions, decl);                
            }
        }
        else
        {
            traverse_function_decls(global_functions, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""external_sema_source->completeVisibleDeclsMap(sema.CurContext);""")
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_function_decls(global_functions, named_decl);
                    }
                }
            }
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (int i = 0; i < global_decls->size(); i++) 
    {
        clang::Decl* decl = (*global_decls)[i]; 
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_function_decls(global_functions, named_decl);
                    }
                }
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : sema.CurContext->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_function_decls(global_functions, named_decl);
        }
    }
    """
    root_interface.ProcessLine(code)      
    root_interface.ProcessLine(b"size_t global_functions_len = global_functions.size();")
    root_interface.ProcessLine(b"const char **global_functions_buffer = global_functions.data();")
    size_address = cpp_to_int(b"global_functions_len")
    data_address = cpp_to_int(b"global_functions_buffer")
    data = vector_to_list(data_address, size_address)
    functions[:] = data
    return list(functions)


def get_cpp_types():
    global types
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* global_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(sema.CurContext, *global_decls);")    
    root_interface.ProcessLine(b"std::vector<clang::Decl*> all_decls;")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> outer_decls;")    
    root_interface.ProcessLine(b"std::vector<const char*> global_types;")    
    code = b"""
    for (int i = 0; i < global_decls->size(); i++)  
    {
        clang::Decl* decl = (*global_decls)[i];           
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::TypeDecl *type_decl = clang::dyn_cast<clang::TypeDecl>(decl2);
                        if (type_decl)
                        {                        
                            global_types.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_type_decls(global_types, decl);                
            }
        }
        else
        {
            traverse_type_decls(global_types, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {      
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::TypeDecl *type_decl = clang::dyn_cast<clang::TypeDecl>(decl2);
                        if (type_decl)
                        {                        
                            global_types.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_type_decls(global_types, decl);                
            }
        }
        else
        {
            traverse_type_decls(global_types, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""external_sema_source->completeVisibleDeclsMap(sema.CurContext);""")
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_type_decls(global_types, named_decl);
                    }
                }
            }
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (int i = 0; i < global_decls->size(); i++) 
    {
        clang::Decl* decl = (*global_decls)[i]; 
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_type_decls(global_types, named_decl);
                    }
                }
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : sema.CurContext->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_type_decls(global_types, named_decl);
        }
    }
    """
    root_interface.ProcessLine(code)      
    root_interface.ProcessLine(b"size_t global_types_len = global_types.size();")
    root_interface.ProcessLine(b"const char **global_types_buffer = global_types.data();")
    size_address = cpp_to_int(b"global_types_len")
    data_address = cpp_to_int(b"global_types_buffer")
    data = vector_to_list(data_address, size_address)
    types[:] = data
    return list(types)


def get_cpp_namespaces():
    global namespaces
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* global_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(sema.CurContext, *global_decls);")    
    root_interface.ProcessLine(b"std::vector<clang::Decl*> all_decls;")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> outer_decls;")      
    root_interface.ProcessLine(b"std::vector<const char*> global_namespaces;")
    code = b"""
    for (int i = 0; i < global_decls->size(); i++)  
    {
        clang::Decl* decl = (*global_decls)[i];
        traverse_namespace_decls(global_namespaces, decl);
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""    
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        traverse_namespace_decls(global_namespaces, decl);
    }    
    """ 
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""external_sema_source->completeVisibleDeclsMap(sema.CurContext);""")
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_namespace_decls(global_namespaces, named_decl);
                    }
                }
            }
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (int i = 0; i < global_decls->size(); i++) 
    {
        clang::Decl* decl = (*global_decls)[i]; 
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_namespace_decls(global_namespaces, named_decl);
                    }
                }
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : sema.CurContext->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_namespace_decls(global_namespaces, named_decl);
        }
    }
    """
    root_interface.ProcessLine(code)          
    root_interface.ProcessLine(b"size_t global_namespaces_len = global_namespaces.size();")
    root_interface.ProcessLine(b"const char **global_namespaces_buffer = global_namespaces.data();")
    size_address = cpp_to_int(b"global_namespaces_len")
    data_address = cpp_to_int(b"global_namespaces_buffer")
    data = vector_to_list(data_address, size_address)
    namespaces[:] = data
    return list(namespaces)


def get_cpp_templates():
    global templates
    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* global_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(sema.CurContext, *global_decls);")    
    root_interface.ProcessLine(b"std::vector<clang::Decl*> all_decls;")
    root_interface.ProcessLine(b"std::vector<clang::Decl*> outer_decls;")    
    root_interface.ProcessLine(b"std::vector<const char*> global_templates;")
    code = b"""
    for (int i = 0; i < global_decls->size(); i++)  
    {
        clang::Decl* decl = (*global_decls)[i];           
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::TemplateDecl *template_decl = clang::dyn_cast<clang::TemplateDecl>(decl2);
                        if (template_decl)
                        {                        
                            global_templates.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_template_decls(global_templates, decl);                
            }
        }
        else
        {
            traverse_template_decls(global_templates, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {      
        clang::NamedDecl *named_decl = clang::dyn_cast<clang::NamedDecl>(decl);                
        if (named_decl)
        {            
            llvm::StringRef name = named_decl->getName();         
            if (name.starts_with("__cling_N"))
            {                
                clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);
                for (clang::Decl *decl2 : ns_decl->noload_decls())
                {                    
                    clang::NamedDecl *named_decl2 = clang::dyn_cast<clang::NamedDecl>(decl2);                    
                    if (named_decl2)
                    {
                        llvm::StringRef name2 = named_decl2->getName();                        	
                        clang::TemplateDecl *template_decl = clang::dyn_cast<clang::TemplateDecl>(decl2);
                        if (template_decl)
                        {                        
                            global_templates.push_back(name2.data());                            
                        }                            
                    }
                }
            }
            else
            {            
                traverse_template_decls(global_templates, decl);                
            }
        }
        else
        {
            traverse_template_decls(global_templates, decl);           
        }
    }    
    """
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""external_sema_source->completeVisibleDeclsMap(sema.CurContext);""")
    code = b"""
    for (clang::Decl *decl : sema.CurContext->noload_decls())
    {
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_template_decls(global_templates, named_decl);
                    }
                }
            }
        }
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (int i = 0; i < global_decls->size(); i++) 
    {
        clang::Decl* decl = (*global_decls)[i]; 
        clang::NamespaceDecl *ns_decl = clang::dyn_cast<clang::NamespaceDecl>(decl);;                
        if (ns_decl)
        {            
            llvm::StringRef name = ns_decl->getName();
            if (name == "std")
            {
                external_sema_source->completeVisibleDeclsMap(ns_decl);
                for (clang::DeclContext::lookup_result result : ns_decl->noload_lookups(true))
                {
                    for (clang::NamedDecl* named_decl : result)
                    {
                        traverse_template_decls(global_templates, named_decl);
                    }
                }
            }
        }
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : sema.CurContext->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_template_decls(global_templates, named_decl);
        }
    }
    """
    root_interface.ProcessLine(code)               
    root_interface.ProcessLine(b"size_t global_templates_len = global_templates.size();")
    root_interface.ProcessLine(b"const char **global_templates_buffer = global_templates.data();")
    size_address = cpp_to_int(b"global_templates_len")
    data_address = cpp_to_int(b"global_templates_buffer")
    data = vector_to_list(data_address, size_address)
    templates[:] = data
    return list(templates)


def get_cpp_names():
    global names
    macros = get_cpp_macros()
    variables = get_cpp_vars()
    functions = get_cpp_functions()
    types = get_cpp_types()
    namespaces = get_cpp_namespaces()
    templates = get_cpp_templates()    
    names[:] = macros + variables + functions + types + namespaces + templates
    names[:] = list(set(names))    
    return list(names)
    
load_cpp_names = get_cpp_names


def get_cpp_member_vars(tclass, static = None):
    code = f"""TList *member_vars = {tclass.name}->GetListOfAllPublicDataMembers();"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"std::vector<const char*> member_names;")
    root_interface.ProcessLine(b"member_names.reserve(1);")
    if static is None:
        code = b"""
        for (TDataMember *member_var : TRangeDynCast<TDataMember>(member_vars))
        {
            member_names.push_back(member_var->GetName());
        }
        """
    elif static is True:
        code = b"""
        for (TDataMember *member_var : TRangeDynCast<TDataMember>(member_vars))
        {
            if ((member_var->Property() & kIsStatic) != 0)
            {
                member_names.push_back(member_var->GetName());
            }
        }
        """
    else:
        code = b"""
        for (TDataMember *member_var : TRangeDynCast<TDataMember>(member_vars))
        {
            if ((member_var->Property() & kIsStatic) == 0)
            {
                member_names.push_back(member_var->GetName());
            }
        }
        """        
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"size_t member_names_len = member_names.size();")
    root_interface.ProcessLine(b"const char **member_names_buffer = member_names.data();")
    size_address = cpp_to_int(b"member_names_len")
    data_address = cpp_to_int(b"member_names_buffer")
    data = vector_to_list(data_address, size_address)
    return data


def get_cpp_member_funcs(tclass, static = None):    
    code = f"""const TList *member_functions = {tclass.name}->GetListOfAllPublicMethods();"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"std::vector<const char*> member_names;")
    root_interface.ProcessLine(b"member_names.reserve(1);")
    if static is None:
        code = b"""
        for (TMethod *member_function : TRangeDynCast<TMethod>(member_functions))
        {
            member_names.push_back(member_function->GetName());
        }
        """
    elif static is True:
        code = b"""
        for (TMethod *member_function : TRangeDynCast<TMethod>(member_functions))
        {
            if ((member_function->Property() & kIsStatic) != 0)
            {
                member_names.push_back(member_function->GetName());
            }
        }
        """
    else:
        code = b"""
        for (TMethod *member_function : TRangeDynCast<TMethod>(member_functions))
        {
            if ((member_function->Property() & kIsStatic) == 0)
            {
                member_names.push_back(member_function->GetName());
            }
        }
        """        
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"size_t member_names_len = member_names.size();")
    root_interface.ProcessLine(b"const char **member_names_buffer = member_names.data();")
    size_address = cpp_to_int(b"member_names_len")
    data_address = cpp_to_int(b"member_names_buffer")
    data = vector_to_list(data_address, size_address)
    return data


def get_cpp_member_templates(tclass, static = None):
    """return all the templates that are accessible through an objcect (not a class).
    In other words, return only the function templates."""
    code = f"""TList *member_func_templates = {tclass.name}->GetListOfFunctionTemplates();"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"std::vector<const char*> member_names;")
    root_interface.ProcessLine(b"member_names.reserve(1);")
    if static is None:
        code = b"""
        for (TFunctionTemplate *member_func_template : TRangeDynCast<TFunctionTemplate>(member_func_templates))
        {
            member_names.push_back(member_func_template->GetName());
        }
        """
    elif static is True:
        code = b"""
        for (TFunctionTemplate *member_func_template : TRangeDynCast<TFunctionTemplate>(member_func_templates))
        {
            if ((member_func_template->Property() & kIsStatic) != 0)
            {
                member_names.push_back(member_func_template->GetName());
            }
        }
        """
    else:
        code = b"""
        for (TFunctionTemplate *member_func_template : TRangeDynCast<TFunctionTemplate>(member_func_templates))
        {
            if ((member_func_template->Property() & kIsStatic) == 0)
            {
                member_names.push_back(member_func_template->GetName());
            }
        }
        """        
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"size_t member_names_len = member_names.size();")
    root_interface.ProcessLine(b"const char **member_names_buffer = member_names.data();")
    size_address = cpp_to_int(b"member_names_len")
    data_address = cpp_to_int(b"member_names_buffer")
    data = vector_to_list(data_address, size_address)
    return data


def get_cpp_members(tclass, static = None):
    member_var_names = get_cpp_member_vars(tclass, static = static)
    member_func_names = get_cpp_member_funcs(tclass, static = static)
    member_template_names = get_cpp_member_templates(tclass, static = static)
    data = member_var_names + member_func_names + member_template_names
    if static is None:
        code = f"""const char *class_name = {tclass.name}->GetName();"""
        code = bytes(code, encoding = "utf-8")
        root_interface.ProcessLine(code)
        address = cpp_to_int(b"class_name")
        p = pyptrs.pointer_to_address(address, ctype = ctypes.c_char_p)
        class_name = pyptrs.dereference(p)
        class_name = class_name.value
        class_name_str = class_name.decode()
        if "<" in class_name_str:
            class_name_str = class_name_str.split("<")
            class_name_str = class_name_str[0]
        for name in list(data):
            name_str = name.decode()
            if name_str.startswith(class_name_str):
                data.remove(name)
    return data


def get_cpp_class_scope(tclass):
    code = f"""TClingClassInfo *class_info = reinterpret_cast<TClingClassInfo*>({tclass.name}->GetClassInfo());"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""clang::Decl *class_decl = class_info->GetDecl();""")
    root_interface.ProcessLine(b"""clang::TagDecl *tag_decl = clang::dyn_cast<clang::TagDecl>(class_decl);""")

    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* all_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(tag_decl, *all_decls);")    
    
    root_interface.ProcessLine(b"std::vector<const char*> in_scope_names;")
    root_interface.ProcessLine(b"in_scope_names.reserve(1);")
    code = b"""
    for (int i = 0; i < all_decls->size(); i++)  
    {
        clang::Decl* decl = (*all_decls)[i];
        traverse_type_decls(in_scope_names, decl);
        traverse_namespace_decls(in_scope_names, decl);
        traverse_template_decls(in_scope_names, decl); 
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::Decl *decl : tag_decl->noload_decls())
    {
        traverse_type_decls(in_scope_names, decl);
        traverse_namespace_decls(in_scope_names, decl);
        traverse_template_decls(in_scope_names, decl); 
    }
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_type_decls(in_scope_names, named_decl);
            traverse_namespace_decls(in_scope_names, named_decl);
            traverse_template_decls(in_scope_names, named_decl); 
        }
    }
    """
    root_interface.ProcessLine(code)                   
    
    root_interface.ProcessLine(b"size_t in_scope_names_len = in_scope_names.size();")
    root_interface.ProcessLine(b"const char **in_scope_names_buffer = in_scope_names.data();")
    size_address = cpp_to_int(b"in_scope_names_len")
    data_address = cpp_to_int(b"in_scope_names_buffer")
    data = vector_to_list(data_address, size_address)
    data += get_cpp_member_vars(tclass, static = True)
    data += get_cpp_member_funcs(tclass, static = True)
    for template in get_cpp_member_templates(tclass, static = False):
        data.remove(template)
    return data


def get_cpp_namespace_scope(tclass):
    code = f"""TClingClassInfo *class_info = reinterpret_cast<TClingClassInfo*>({tclass.name}->GetClassInfo());"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""clang::Decl *class_decl = class_info->GetDecl();""")
    root_interface.ProcessLine(b"""clang::NamespaceDecl *namespace_decl = clang::dyn_cast<clang::NamespaceDecl>(class_decl);""")

    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* all_decls = new clang::SmallVector<clang::Decl*>;")
    root_interface.ProcessLine(b"external_sema_source->FindExternalLexicalDecls(namespace_decl, *all_decls);")    
    
    root_interface.ProcessLine(b"std::vector<const char*> in_scope_names;")
    root_interface.ProcessLine(b"in_scope_names.reserve(1);")
    code = b"""
    for (int i = 0; i < all_decls->size(); i++)  
    {
        clang::Decl* decl = (*all_decls)[i];
        traverse_object_decls(in_scope_names, decl);
        traverse_function_decls(in_scope_names, decl);
        traverse_type_decls(in_scope_names, decl);
        traverse_namespace_decls(in_scope_names, decl);
        traverse_template_decls(in_scope_names, decl); 
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::Decl *decl : namespace_decl->noload_decls())
    {
        traverse_object_decls(in_scope_names, decl);
        traverse_function_decls(in_scope_names, decl);
        traverse_type_decls(in_scope_names, decl);
        traverse_namespace_decls(in_scope_names, decl);
        traverse_template_decls(in_scope_names, decl); 
    }    
    """
    root_interface.ProcessLine(code)
    code = b"""
    for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
    {
        for (clang::NamedDecl* named_decl : result)
        {
            traverse_object_decls(in_scope_names, named_decl);
            traverse_function_decls(in_scope_names, named_decl);
            traverse_type_decls(in_scope_names, named_decl);
            traverse_namespace_decls(in_scope_names, named_decl);
            traverse_template_decls(in_scope_names, named_decl); 
        }
    }
    """
    root_interface.ProcessLine(code)                   
    root_interface.ProcessLine(b"size_t in_scope_names_len = in_scope_names.size();")
    root_interface.ProcessLine(b"const char **in_scope_names_buffer = in_scope_names.data();")
    size_address = cpp_to_int(b"in_scope_names_len")
    data_address = cpp_to_int(b"in_scope_names_buffer")
    data = vector_to_list(data_address, size_address)
    return data


def get_partial_cpp_scope(tclass, name_type):
    code = f"""TClingClassInfo *class_info = reinterpret_cast<TClingClassInfo*>({tclass.name}->GetClassInfo());"""
    code = bytes(code, encoding = "utf-8")
    root_interface.ProcessLine(code)
    root_interface.ProcessLine(b"""clang::Decl *class_decl = class_info->GetDecl();""")
    root_interface.ProcessLine(b"""clang::TagDecl *tag_decl = clang::dyn_cast<clang::TagDecl>(class_decl);""")
    root_interface.ProcessLine(b"""clang::NamespaceDecl *namespace_decl = clang::dyn_cast<clang::NamespaceDecl>(class_decl);""")

    root_interface.ProcessLine(b"""TCling *root_interpreter = dynamic_cast<TCling*>(gInterpreter);""")
    root_interface.ProcessLine(b"""cling::Interpreter *real_interpreter = root_interpreter->GetInterpreterImpl();""")
    root_interface.ProcessLine(b"""clang::CompilerInstance *compiler_instance = real_interpreter->m_IncrParser->getCI();""")
    root_interface.ProcessLine(b"""clang::Sema &sema = compiler_instance->getSema();""")
    root_interface.ProcessLine(b"""clang::ASTContext &ast_context = sema.Context;""")
    root_interface.ProcessLine(b"""clang::IntrusiveRefCntPtr<clang::ExternalSemaSource> external_sema_source = sema.ExternalSource;""")          
    root_interface.ProcessLine(b"clang::SmallVector<clang::Decl*>* all_decls = new clang::SmallVector<clang::Decl*>;")
    code = b"""
    if (tag_decl)
    {
        external_sema_source->FindExternalLexicalDecls(tag_decl, *all_decls);
    }
    else
    {
        external_sema_source->FindExternalLexicalDecls(namespace_decl, *all_decls);
    }
    """
    root_interface.ProcessLine(code)
    if name_type == "variable":
        code = b"""
        std::vector<const char*> variable_names;
        variable_names.reserve(1);
        if (tag_decl)
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_object_decls(variable_names, decl);
            }    
        
            for (clang::Decl *decl : tag_decl->noload_decls())
            {
                traverse_object_decls(variable_names, decl);
            }

            for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_object_decls(variable_names, named_decl); 
                }
            }            
        }
        else
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_object_decls(variable_names, decl);
            }    
        
            for (clang::Decl *decl : namespace_decl->noload_decls())
            {
                traverse_object_decls(variable_names, decl);
            }

            for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_object_decls(variable_names, named_decl); 
                }
            }                        
        }
        """
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"size_t variable_names_len = variable_names.size();")
        root_interface.ProcessLine(b"const char **variable_names_buffer = variable_names.data();")
        size_address = cpp_to_int(b"variable_names_len")
        data_address = cpp_to_int(b"variable_names_buffer")        
    elif name_type == "function":
        code = b"""
        std::vector<const char*> function_names;
        function_names.reserve(1);
        if (tag_decl)
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_function_decls(function_names, decl);
            }    
        
            for (clang::Decl *decl : tag_decl->noload_decls())
            {
                traverse_function_decls(function_names, decl);
            }

            for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_function_decls(function_names, named_decl); 
                }
            }            
        }
        else
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_function_decls(function_names, decl);
            }    
        
            for (clang::Decl *decl : namespace_decl->noload_decls())
            {
                traverse_function_decls(function_names, decl);
            }

            for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_function_decls(function_names, named_decl); 
                }
            }                        
        }
        """
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"size_t function_names_len = function_names.size();")
        root_interface.ProcessLine(b"const char **function_names_buffer = function_names.data();")
        size_address = cpp_to_int(b"function_names_len")
        data_address = cpp_to_int(b"function_names_buffer")    
    elif name_type == "type":
        code = b"""
        std::vector<const char*> type_names;
        type_names.reserve(1);
        if (tag_decl)
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_type_decls(type_names, decl);
            }    
        
            for (clang::Decl *decl : tag_decl->noload_decls())
            {
                traverse_type_decls(type_names, decl);
            }

            for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_type_decls(type_names, named_decl); 
                }
            }            
        }
        else
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_type_decls(type_names, decl);
            }    
        
            for (clang::Decl *decl : namespace_decl->noload_decls())
            {
                traverse_type_decls(type_names, decl);
            }

            for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_type_decls(type_names, named_decl); 
                }
            }                        
        }
        """
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"size_t type_names_len = type_names.size();")
        root_interface.ProcessLine(b"const char **type_names_buffer = type_names.data();")
        size_address = cpp_to_int(b"type_names_len")
        data_address = cpp_to_int(b"type_names_buffer")
    elif name_type == "namespace":
        code = b"""
        std::vector<const char*> namespace_names;
        namespace_names.reserve(1);
        if (tag_decl)
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_namespace_decls(namespace_names, decl);
            }    
        
            for (clang::Decl *decl : tag_decl->noload_decls())
            {
                traverse_namespace_decls(namespace_names, decl);
            }

            for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_namespace_decls(namespace_names, named_decl); 
                }
            }            
        }
        else
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_namespace_decls(namespace_names, decl);
            }    
        
            for (clang::Decl *decl : namespace_decl->noload_decls())
            {
                traverse_namespace_decls(namespace_names, decl);
            }

            for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_namespace_decls(namespace_names, named_decl); 
                }
            }                        
        }
        """
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"size_t namespace_names_len = namespace_names.size();")
        root_interface.ProcessLine(b"const char **namespace_names_buffer = namespace_names.data();")
        size_address = cpp_to_int(b"namespace_names_len")
        data_address = cpp_to_int(b"namespace_names_buffer")
    elif name_type == "template":
        code = b"""
        std::vector<const char*> template_names;
        template_names.reserve(1);
        if (tag_decl)
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_template_decls(template_names, decl);
            }    
        
            for (clang::Decl *decl : tag_decl->noload_decls())
            {
                traverse_template_decls(template_names, decl);
            }

            for (clang::DeclContext::lookup_result result : tag_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_template_decls(template_names, named_decl); 
                }
            }            
        }
        else
        {
            for (int i = 0; i < all_decls->size(); i++)  
            {
                clang::Decl* decl = (*all_decls)[i];
                traverse_template_decls(template_names, decl);
            }    
        
            for (clang::Decl *decl : namespace_decl->noload_decls())
            {
                traverse_template_decls(template_names, decl);
            }

            for (clang::DeclContext::lookup_result result : namespace_decl->noload_lookups(true))
            {
                for (clang::NamedDecl* named_decl : result)
                {
                    traverse_template_decls(template_names, named_decl); 
                }
            }                        
        }
        """
        root_interface.ProcessLine(code)
        root_interface.ProcessLine(b"size_t template_names_len = template_names.size();")
        root_interface.ProcessLine(b"const char **template_names_buffer = template_names.data();")
        size_address = cpp_to_int(b"template_names_len")
        data_address = cpp_to_int(b"template_names_buffer")
    data = vector_to_list(data_address, size_address)
    return data
    
    
