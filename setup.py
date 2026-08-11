import setuptools
import subprocess
import os
import shutil
        

def main():
    cd = os.getcwd()
    root_dir = os.path.join(cd, "src", "rootwin", "root")
    os.chdir(root_dir)
    print("generating the .pch...")
    process = subprocess.run("python makepch.py allDict.cxx.pch", shell = True, creationflags = subprocess.CREATE_NO_WINDOW)
    print("successful.")
    shutil.move("allDict.cxx.pch", "etc")
    os.chdir(cd)
    setuptools.setup()


main()
