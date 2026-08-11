#ifndef ROOT_RConfigure
#define ROOT_RConfigure

/* Configurations file for win64 */

/* #undef R__HAVE_CONFIG */

#ifdef R__HAVE_CONFIG
#define ROOTPREFIX    "$(ROOTSYS)"
#define ROOTBINDIR    "$(ROOTSYS)/bin"
#define ROOTLIBDIR    "$(ROOTSYS)/lib"
#define ROOTETCDIR    "$(ROOTSYS)/etc"
#define ROOTDATADIR   "$(ROOTSYS)/."
#define ROOTDOCDIR    "$(ROOTSYS)/."
#define ROOTMACRODIR  "$(ROOTSYS)/macros"
#define ROOTTUTDIR    "$(ROOTSYS)/tutorials"
#define ROOTSRCDIR    "$(ROOTSYS)/src"
#define ROOTICONPATH  "$(ROOTSYS)/icons"
#define TTFFONTDIR    "$(ROOTSYS)/fonts"
#endif

#define EXTRAICONPATH ""

#define ROOT__cplusplus 201703L
#if defined(__cplusplus) && (__cplusplus != ROOT__cplusplus)
# if defined(_MSC_VER)
#  pragma message(__FILE__ ": Warning: The C++ standard in this build does not match ROOT configuration (201703L); this might cause unexpected issues. And please make sure you are using the -Zc:__cplusplus compilation flag")
# else
#  warning "The C++ standard in this build does not match ROOT configuration (201703L); this might cause unexpected issues"
# endif
#endif

#undef R__HAS_SETRESUID   /**/
#define R__HAS_MATHMORE   /**/
#undef R__HAS_PTHREAD    /**/
#undef R__HAS_XFT    /**/
#define R__HAS_CLAD    /**/
#undef R__HAS_COCOA    /**/
#undef R__HAS_VDT    /**/
#undef R__HAS_STD_EXPERIMENTAL_SIMD    /**/
#undef R__EXPERIMENTAL_SIMD_PIN_AVX_ABI    /**/
#undef R__USE_CXXMODULES   /**/
#undef R__USE_LIBCXX    /**/
#undef R__HAS_ATTRIBUTE_ALWAYS_INLINE /**/
#undef R__HAS_ATTRIBUTE_NOINLINE /**/
#define R__USE_IMT   /**/
#undef R__COMPLETE_MEM_TERMINATION /**/
#undef R__HAS_CEFWEB  /**/
#undef R__HAS_QT6WEB  /**/
#undef R__HAS_DAVIX  /**/
#define R__HAS_CURL  /**/
#define R__HAS_DATAFRAME /**/
#define R__HAS_ROOT7 /**/
#undef R__LESS_INCLUDES /**/
#define R__HARDWARE_INTERFERENCE_SIZE 64
 /*Determined at CMake configure to be stable across all TUs*/

#undef R__HAS_ZLIB_NG /**/

#define R__HAS_TMVACPU /**/
#undef R__HAS_TMVAGPU /**/
#undef R__HAS_CUDNN /**/
#undef R__HAS_PYMVA /**/
#undef R__HAS_RMVA /**/

#undef R__HAS_URING /**/

#define R__HAS_GEOM /**/

#endif
