# Auxiliary file containing functions for parallelization

import multiprocessing
import time
import math
from psutil import virtual_memory

# Global variables within module's scope
__start_time_for_x = 0
__x_marker = 0


def __output(log, indicator="TOP"):
    """ Helper function to store in a file the logged output of multiple processes

    :param log: text to log
    :type log: str or list
    :param indicator: indicate the level or pid a log report came from
    :type indicator: str

    :return: None
    :rtype: None
    """
    f = open('output-parallel.log', 'a')
    f.write(str(indicator) + " @@@ " + str(log) + "\n")
    f.close()


def __check_avail_mem():
    """ Check that there is at least 20% available memory

    :return: whether memory is less than 80%
    :rtype: bool
    """
    if virtual_memory().percent > 80:
        __output("Holding pattern...")
        return False
    else:
        return True


def mark_time(spacer=False):
    """ Marks the time for event tracking and optimization purposes

    :param spacer: add a space when printing time
    :type spacer: bool

    :return: number of seconds elapsed
    :rtype: float
    """
    global __start_time_for_x
    global __x_marker
    if __start_time_for_x == 0:
        __start_time_for_x = time.time()
        __x_marker += 1
    else:
        time_diff = round(time.time() - __start_time_for_x, 4)
        print("#" + str(__x_marker) + " Time took: " + str(time_diff))
        if spacer:
            print("-----")
            __start_time_for_x = 0
            __x_marker = 0
            return time_diff
        else:
            __start_time_for_x = time.time()
            __x_marker += 1


def parallel_process(processes, process_list, input_function):
    """ Marks the time for event tracking and optimization purposes

     :param processes: number of processes that can run in parallel
     :type processes: int
     :param process_list: list to be processed by the parallel function
     :type process_list: list
     :param input_function: function to execute the parallel process. Functions receives as a first argument element
     from the process list
     :type input_function: def

     :return: None
     :rtype: None
     """
    a = 0
    all_records = process_list
    all_active = []
    while a < len(all_records):
        time.sleep(0.5)
        if __check_avail_mem():
            # Check all active scripts if they are still active
            for p in all_active:
                if not p.is_alive():  # Existing connection false, replace it with a new one
                    p.join()
                    all_active.remove(p)
                    p_new = multiprocessing.Process(target=input_function, args=([all_records[a], ]))
                    all_active.append(p_new)
                    __output(all_active)
                    all_active[len(all_active) - 1].start()
                    a += 1
                    mem = virtual_memory()
                    __output("Mem used: " + str(mem.percent))
            if len(all_active) < processes:  # do the same
                p_new = multiprocessing.Process(target=input_function, args=([all_records[a], ]))
                all_active.append(p_new)
                __output(all_active)
                all_active[len(all_active) - 1].start()
                a += 1
                mem = virtual_memory()
                __output("Mem used: " + str(mem.percent))
    __output("done")


def test(x):
    """ Test example for calculating logarithm

    :param x: number
    :type x: int

    :return: logarithm
    :rtype: float
    """

    print(math.log(x))
    return math.log(x)


if __name__ == "__main__":
    # Test example
    parallel_process(7, [1, 2, 3, 4, 5, 6], test)
