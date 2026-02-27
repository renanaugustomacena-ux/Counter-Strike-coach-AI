import os
import sys

import numpy as np
import torch
from sqlmodel import select

# --- Path Stabilization ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager


def run_training_cycle():
    manager = CoachTrainingManager()
    manager.run_full_cycle()


if __name__ == "__main__":
    run_training_cycle()
