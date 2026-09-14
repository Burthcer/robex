# Task 1: Intelligent Multiline Input, Spell Correction & Command Normalization

## Objective
Build a lightweight, typo-tolerant natural language command normalizer supporting multiline speech-to-text dictation and pasted paragraphs while keeping RAM usage negligible (<50 MB) and zero VRAM footprint.

## Target Files
- `src/robex/ai/normalizer.py` [NEW]
- `src/robex/ai/__init__.py` [MODIFY]
- `src/robex/ai/commander.py` [MODIFY]
- `tests/test_normalizer.py` [NEW]
- `tests/test_commander.py` [MODIFY]

## Actionable Checklist
1. Create `src/robex/ai/normalizer.py` implementing `TextNormalizer` with algorithmic fuzzy matching (using Python's standard library `difflib.get_close_matches`), spelling correction for game/macro keywords (verbs: `click`, `press`, `hold`, `wait`, `jump`; colors: `green`, `red`, `blue`, `yellow`, `orange`; keys: `space`, `shift`, `w`, `a`, `s`, `d`), and synonym mapping (`tap` -> `press`, `walk` -> `hold w`).
2. Implement speech-to-text cleaning routines in `TextNormalizer` that strip conversational filler phrases (`"please"`, `"could you"`, `"um"`, `"uh"`, `"hey"`, `"now"`) and segment multiline paragraphs into standardized sequential action clauses.
3. Integrate `TextNormalizer` into `CommandParser` in `src/robex/ai/commander.py` so incoming raw or dictated text is automatically cleaned and spell-corrected before action tokenization.
4. Create comprehensive unit tests in `tests/test_normalizer.py` and extend `tests/test_commander.py` verifying typo correction (e.g. `"clck gern botton"` -> `"click green button"`), speech filler removal, multiline paragraph parsing, and zero regression.

## Constraints
- **Strict Resource Budget**: Do NOT import heavy transformer libraries (e.g., PyTorch, HuggingFace, spaCy); use only standard library modules (`difflib`, `re`) so execution remains well within the 4 GB RAM ceiling and uses 0 GB VRAM.
- **Documentation Integrity**: Never delete existing comments, docstrings, or structure in `src/robex/ai/commander.py` and related files.
- **Backward Compatibility**: All existing 17 unit tests in the test suite must continue to pass without error.

## Verification Command
```powershell
.\venv\Scripts\pytest tests/ -v
```
