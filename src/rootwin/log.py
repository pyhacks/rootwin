import os


dir_name = os.path.split(__file__)[0]
log_flag = True


def log(string):
    if log_flag:
        print(string)


def enable_logging():
    cd = os.getcwd()
    os.chdir(dir_name)    
    with open("log_flag.txt", "w") as f:
        f.write("1")
    os.chdir(cd)


def disable_logging():
    cd = os.getcwd()
    os.chdir(dir_name)        
    with open("log_flag.txt", "w") as f:
        f.write("0")
    os.chdir(cd)


def init():
    global log_flag
    cd = os.getcwd()
    os.chdir(dir_name)
    with open("log_flag.txt", "r") as f:
        log_flag = f.read()
        log_flag = int(log_flag)
    os.chdir(cd)


init()
