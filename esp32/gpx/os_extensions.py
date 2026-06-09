import os

def file_exists(path):
    """Return True if path exists. Uses os.stat for MicroPython compatibility."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False
    except Exception:
        # some ports raise different errors
        try:
            os.stat(path)
            return True
        except Exception:
            return False
