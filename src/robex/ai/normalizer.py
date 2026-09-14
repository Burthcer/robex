"""Lightweight, typo-tolerant text normalizer for dictated or pasted macro commands.

Uses only the Python standard library (``difflib`` + ``re``) so it stays well within
the project's strict RAM/VRAM budget -- no transformer or NLP model dependencies.
"""

import re
import difflib

# Domain vocabulary eligible for fuzzy spell-correction. Keeping this list small and
# specific (rather than a full dictionary) is what keeps difflib matching fast and safe.
_VERBS = ["click", "press", "hold", "wait", "jump"]
_COLORS = ["green", "red", "blue", "yellow", "orange"]
_KEYS = ["space", "shift", "w", "a", "s", "d"]
# Extra command nouns/units that show up in the same clauses as the words above --
# without these, typos like "botton" -> "button" would have nothing to match against.
_EXTRA = ["button", "seconds", "second"]

VOCAB = sorted(set(_VERBS + _COLORS + _KEYS + _EXTRA))

# Common short connector words that must never be "corrected" into vocab lookalikes.
_STOPWORDS = {
    "a", "an", "the", "on", "at", "to", "of", "is", "for", "and", "then",
    "with", "in", "it", "its", "this", "that",
}

# Conversational speech-to-text filler removed before parsing. Longer phrases first so
# "could you" is stripped whole rather than leaving a dangling "you".
_FILLERS = ["could you", "please", "um", "uh", "hey", "now"]
_FILLER_RE = re.compile(r"\b(?:" + "|".join(re.escape(f) for f in _FILLERS) + r")\b", re.IGNORECASE)

# Synonym mapping applied after spell-correction. Values may expand to multiple words.
_SYNONYMS = {
    "tap": "press",
    "walk": "hold w",
}

_WORD_RE = re.compile(r"[A-Za-z']+")

# Multiline paragraphs / dictation are segmented into clauses on newlines and sentence
# stops so each becomes its own standardized action clause (joined back with "; ").
# The period lookaround avoids splitting decimal durations like "1.5s".
_CLAUSE_SPLIT_RE = re.compile(r"[\n\r!]+|(?<!\d)\.(?!\d)")


class TextNormalizer:
    """Cleans and spell-corrects raw or dictated text before command tokenization."""

    def _correct_word(self, word: str) -> str:
        """Fuzzy-corrects a single word against the known macro vocabulary.

        Candidates must also share the word's first letter -- this keeps the cutoff
        low enough to catch real typos (e.g. "gern" -> "green") without also mangling
        unrelated words that merely have similar letter shapes (e.g. "double" staying
        "double" instead of getting rewritten to "blue").
        """
        lw = word.lower()
        if lw in VOCAB or lw in _STOPWORDS or len(lw) < 3:
            return lw
        matches = difflib.get_close_matches(lw, VOCAB, n=3, cutoff=0.6)
        matches = [m for m in matches if m[0] == lw[0]]
        return matches[0] if matches else lw

    def _normalize_clause(self, clause: str) -> str:
        """Spell-corrects and applies synonym mapping to a single action clause."""
        if not _WORD_RE.search(clause):
            return clause.strip()

        def _fix(match: "re.Match[str]") -> str:
            corrected = self._correct_word(match.group(0))
            return _SYNONYMS.get(corrected, corrected)

        cleaned = _WORD_RE.sub(_fix, clause)
        return re.sub(r"\s+", " ", cleaned).strip()

    def strip_fillers(self, text: str) -> str:
        """Removes conversational speech-to-text filler words/phrases.

        Collapses stray whitespace within each line, but keeps line breaks intact --
        they matter for segmenting multiline dictation/pasted paragraphs below.
        """
        lines = text.split("\n")
        cleaned_lines = [re.sub(r"\s+", " ", _FILLER_RE.sub(" ", line)).strip() for line in lines]
        return "\n".join(cleaned_lines)

    def normalize(self, text: str) -> str:
        """Cleans filler, spell-corrects vocabulary, and segments multiline paragraphs
        into a single string of ``; ``-joined standardized action clauses."""
        if not text or not text.strip():
            return ""

        cleaned = self.strip_fillers(text)
        raw_clauses = [c for c in _CLAUSE_SPLIT_RE.split(cleaned) if c.strip()]

        normalized_clauses = [self._normalize_clause(c) for c in raw_clauses]
        normalized_clauses = [c for c in normalized_clauses if c]

        return "; ".join(normalized_clauses)


# Global normalizer instance
normalizer = TextNormalizer()
