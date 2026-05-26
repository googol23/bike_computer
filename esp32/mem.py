import gc

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