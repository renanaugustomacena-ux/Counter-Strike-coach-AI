import numpy as np
import pandas as pd
from scipy.stats import entropy


class BrainFeatureEngineer:
    def __init__(self):
        self.combat_window = 5.0

    def calculate_combat_stress_index(self, health, enemies_in_fov, distance_to_enemy):
        danger_factor = (101 - health) / 100.0
        fov_factor = np.log1p(enemies_in_fov)
        dist_factor = np.sqrt(max(1, distance_to_enemy))
        return (danger_factor * fov_factor) / dist_factor

    def process_match_snapshot(self, data):
        csi = self.calculate_combat_stress_index(
            data.get("health", 100), data.get("enemies_visible", 0), data.get("dist_to_enemy", 1000)
        )
        econ = data.get("equipment_value", 0) / max(1, data.get("team_avg_eqp", 1))
        urgency = 1.0 / (data.get("time_left", 115) + 1e-6)
        precision = data.get("hits", 0) / max(1, data.get("shots", 1))
        mobility = data.get("avg_speed", 0) * data.get("dist_from_spawn", 0) / 1000.0

        return {
            "csi": csi,
            "economic_pressure": econ,
            "tactical_urgency": urgency,
            "mechanical_precision": precision,
            "mobility_aggression": mobility,
        }
