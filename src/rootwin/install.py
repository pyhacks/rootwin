import subprocess
import os
import shutil
        

def install():
    print("Running rootwin post installation script...")    
    cd = os.getcwd()
    dir_name = os.path.split(__file__)[0]
    root_dir = os.path.join(dir_name, "root")
    os.chdir(root_dir)
    print("generating the .pch...")
    process = subprocess.run("python makepch.py allDict.cxx.pch", shell = True, creationflags = subprocess.CREATE_NO_WINDOW)
    print("successful.")
    try:
        shutil.move("allDict.cxx.pch", "etc")
    except shutil.Error:
        os.remove("etc/allDict.cxx.pch")
        shutil.move("allDict.cxx.pch", "etc")
    os.chdir(cd)


def main():
    dir_name = os.path.split(__file__)[0]
    config_path = os.path.join(dir_name, "isinstalled.txt")
    with open(config_path, "r+") as f:
        is_installed = f.read()
        f.seek(0)        
        if is_installed == "false":
            install()
            f.write("true ")
    
main()
