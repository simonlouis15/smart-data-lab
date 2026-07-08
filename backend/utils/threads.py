import threading

"""
Helper functions to enable multithreading
"""

def start_threads(threads: list):
    """
    Start all threads in the provided list.
    
    Args:
        threads: List of threading.Thread objects to start
    """
    for thread in threads:
        thread.start()

def join_threads(threads: list):
    """
    Wait for all threads in the provided list to complete.
    
    Args:
        threads: List of threading.Thread objects to join
    """
    for thread in threads:
        thread.join()

def run_functions_parallel(functions: list, with_args: bool = False):
    """
    Run a list of functions in parallel using threads.
    
    Args:
        functions: List of functions to run, or list of (function, args) tuples if with_args=True
        with_args: If True, functions list contains (function, args) tuples
    
    Returns:
        List of thread objects
    """
    threads = []
    
    if with_args:
        for func, args in functions:
            thread = threading.Thread(target=func, args=args)
            threads.append(thread)
    else:
        for func in functions:
            thread = threading.Thread(target=func)
            threads.append(thread)
    
    start_threads(threads)
    join_threads(threads)
    
    return threads