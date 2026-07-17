import multiprocessing
import os
import sys


def hook():
    # 1. Mandatory for Windows Compiled Binaries using daemons/workers
    multiprocessing.freeze_support()

    # 2. Path Stabilization for Frozen Environment
    if getattr(sys, "frozen", False):
        # Set the working directory to the executable's directory
        # to ensure relative paths like 'data/' and 'PHOTO_GUI/' work.
        # R4 LOW: _MEIPASS is PyInstaller-specific — other freezers
        # (cx_Freeze, Nuitka) set sys.frozen without it, and the bare
        # attribute access raised AttributeError at import.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            os.chdir(meipass)


hook()
