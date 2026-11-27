log_flag = True


def log(string):
    if log_flag:
        print(string)


def enable_logging():
    global log_flag
    log_flag = True


def disable_logging():
    global log_flag
    log_flag = False
