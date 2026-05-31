import gc
import gc
import time
import micropython

def usage(label=""):
    gc.collect()

    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc

    print("------", label, "------")
    print("Free:      ", free)
    print("Allocated: ", alloc)
    print("Total:     ", total)
    print("Usage:     {:.1f}%".format(alloc / total * 100))


class MemProfiler:
    def __init__(self, label="mem"):
        self.label = label
        self.last_free = 0

    def snapshot(self):
        gc.collect()

        free = gc.mem_free()
        alloc = gc.mem_alloc()

        delta = free - self.last_free
        self.last_free = free

        print(
            "{} | free:{} | alloc:{} | delta:{}"
            .format(self.label, free, alloc, delta)
        )

    def heap_dump(self):
        gc.collect()
        micropython.mem_info()