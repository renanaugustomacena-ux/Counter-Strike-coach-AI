import multiprocessing
import os
import sys


def hook():
    # 1. Mandatory for Windows Compiled Binaries using daemons/workers
    multiprocessing.freeze_support()

    # 2. Path Stabilization for Frozen Environment
    if getattr(sys, "frozen", False):
        # Set the working directory to the executable's directory
        # to ensure relative paths like 'data/' and 'PHOTO_GUI/' work
        os.chdir(sys._MEIPASS)


hook()
