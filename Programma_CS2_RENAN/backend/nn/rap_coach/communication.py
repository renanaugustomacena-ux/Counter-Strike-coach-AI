import numpy as np
import torch

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.rap_coach.communication")


class RAPCommunication:
    """
    Pedagogical Feedback Generator.
    Translates causal attribution into templated advice.

    Adheres to Layer 5: Multi-Timescale & Skill Modeling.
    """

    def __init__(self):
        # Level-stratified templates
        self.templates = {
            "low": {  # Level 1-3: Direct, Concrete
                "positioning": "Watch your back. You were exposed to {angle} for {time}s without checking.",
                "mechanics": "Stop moving before you shoot. Your counter-strafing was off by {error}ms.",
                "strategy": "Stick with the team. You are entering sites alone too often.",
            },
            "mid": {  # Level 4-7: Pattern-based
                "positioning": "Your site anchoring is {score}% optimal, but you over-rotate when utility lands.",
                "mechanics": "Burst control is solid, but your crosshair height dropped during the {time}s spray.",
                "strategy": "Team economy suggests a {recommendation} play. Consider saving utility for the retake.",
            },
            "high": {  # Level 8-10: Strategic / Abstract
                "positioning": "Professional positioning suggests a {angle} lurk here would have 2x advantage.",
                "mechanics": "Flick stability is high, but you are favoring left-side peeks by {error}%.",
                "strategy": "Conditioning successful. They expect an A push; a {recommendation} pivot now is optimal.",
            },
        }

    def generate_advice(self, layer_outputs, confidence, skill_level: int = 5):
        """
        Applies the 'Skill-Conditioned Explanation' rule.
        """
        if confidence < 0.7:
            logger.debug("Advice suppressed: confidence %.2f below threshold 0.7", confidence)
            return None

        # 1. Determine Tier
        if skill_level <= 3:
            tier = "low"
        elif skill_level <= 7:
            tier = "mid"
        else:
            tier = "high"

        # 2. Extract Top Signal
        with torch.no_grad():
            scores = (
                layer_outputs.squeeze().cpu().numpy()
                if hasattr(layer_outputs, "squeeze")
                else [0.1]
            )
            top_idx = int(np.argmax(scores)) if len(scores.shape) > 0 else 0

            topics = ["positioning", "mechanics", "strategy"]
            topic = topics[top_idx % len(topics)]

            # 3. Format based on tier templates
            template = self.templates[tier][topic]

            # NOTE (F3-37): `angle` always resolves to "the flank" — advice appears
            # dynamic but is templated with a static value. Replace with an actual
            # spatial analysis (e.g. nearest choke point from PlayerKnowledge) when
            # game-context data is available at this call site.
            return template.format(
                score=int(confidence * 100),
                time=round(float(confidence * 2), 1),
                error=int((1 - confidence) * 300),
                angle="the flank",
                recommendation="conservative" if confidence > 0.8 else "aggressive",
            )
