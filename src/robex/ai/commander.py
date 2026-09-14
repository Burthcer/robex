"""Natural language command interpreter for converting plain English prompts into macro actions."""

import re
import logging
from typing import List, Optional

from robex.engine.actions import (
    Action,
    ClickAction,
    VisionClickAction,
    KeyPressAction,
    KeyHoldAction,
    StuntAction,
    WaitAction,
)
from robex.ai.normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class CommandParser:
    """Interprets user prompt commands (e.g. 'Click green button, then jump, then hold W for 2s')."""

    def __init__(self) -> None:
        # Cleans speech-to-text filler and spell-corrects vocabulary before tokenization.
        self.normalizer = TextNormalizer()

    def parse_instruction(self, text: str) -> List[Action]:
        """Parses compound or single natural language commands into a sequence of Action objects."""
        if not text or not text.strip():
            return []

        # Strip dictation filler, fix typos, and segment multiline/pasted paragraphs
        # into standardized clauses before applying the delimiter split below.
        text = self.normalizer.normalize(text)
        if not text:
            return []

        # Split on delimiters: 'then', ', then', 'and then', ';', or newlines
        delimiters = r"(?:,\s*(?:and\s+)?then\s+|\s+(?:and\s+)?then\s+|;\s*|\n+)"
        clauses = [c.strip(" \t\r\n,;.") for c in re.split(delimiters, text, flags=re.IGNORECASE) if c.strip(" \t\r\n,;.")]

        actions: List[Action] = []
        for clause in clauses:
            act = self._parse_single_clause(clause)
            if act:
                actions.append(act)
            else:
                logger.warning("Could not interpret command clause: '%s'", clause)

        return actions

    def _parse_single_clause(self, clause: str) -> Optional[Action]:
        """Parses a single atomic clause into an Action."""
        s = clause.lower().strip()

        # 1. Vision Click: e.g. "click green button", "click on the red button", "press the blue button"
        match_vision = re.search(r"(?:click|tap|press)(?:\s+on)?(?:\s+the)?\s+([a-z]+)\s+button", s)
        if match_vision:
            color = match_vision.group(1)
            return VisionClickAction(target_color=color, timeout_sec=3.0)

        # 2. Absolute Click: e.g. "click at 450, 300" or "click (450, 300)"
        match_coords = re.search(r"click(?:\s+at)?\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?", s)
        if match_coords:
            x, y = int(match_coords.group(1)), int(match_coords.group(2))
            return ClickAction(x=x, y=y)

        # 3. Simple Click (no coords, no color): e.g. "click" or "left click"
        if re.match(r"^(?:left\s+)?click(?:\s+mouse)?$", s):
            # Click at current position or default
            return ClickAction(x=0, y=0, clicks=1)

        # 4. Wait / Pause: e.g. "wait 2 seconds", "wait 0.5s", "sleep 1s"
        match_wait = re.search(r"(?:wait|sleep|delay)\s+(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?", s)
        if match_wait:
            duration = float(match_wait.group(1))
            return WaitAction(duration=duration)

        # 5. Stunts: e.g. "double jump", "jump forward", "turn around", "turn 180"
        if "double jump" in s:
            return StuntAction(stunt_name="double_jump")
        if "jump forward" in s:
            return StuntAction(stunt_name="jump_forward")
        if "turn around" in s or "turn 180" in s:
            return StuntAction(stunt_name="turn_180")

        # 6. Key Hold / Movement: e.g. "hold w for 3 seconds", "walk forward for 2.5s", "run for 4s"
        match_hold = re.search(r"hold\s+([a-z0-9_]+)\s+for\s+(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?", s)
        if match_hold:
            key = match_hold.group(1)
            duration = float(match_hold.group(2))
            return KeyHoldAction(key=key, duration=duration)

        match_walk = re.search(r"(?:walk|run|move\s+forward)\s+for\s+(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?", s)
        if match_walk:
            duration = float(match_walk.group(1))
            return KeyHoldAction(key="w", duration=duration)

        # 7. Key Press: e.g. "press space", "jump", "press e", "tap shift"
        if s in ("jump", "press jump"):
            return KeyPressAction(key="space", duration=0.08)

        match_press = re.search(r"(?:press|tap)\s+([a-z0-9_]+)", s)
        if match_press:
            key = match_press.group(1)
            return KeyPressAction(key=key, duration=0.05)

        return None


# Global command parser instance
parser = CommandParser()
