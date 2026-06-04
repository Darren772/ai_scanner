"""
Gemini prompt templates, one per check mode.
Each function returns a string prompt to be sent alongside the screenshot image.

The prompts instruct Gemini to respond in clearly labelled sections so that
parse_response() in api/gemini.py can split the output deterministically.
"""

_SECTION_INSTRUCTIONS = """\
Return your feedback in exactly these labelled sections:

## GRAMMAR
List each grammar issue on a new line, prefixed with a dash.

## SPELLING
List each spelling error on a new line, prefixed with a dash.

## STRUCTURE
List each structure/flow suggestion on a new line, prefixed with a dash.

## TONE
List each tone observation on a new line, prefixed with a dash.

## REWRITE
Provide a clean corrected version of the full text.

If a section has no issues, write "None found." under that heading.\
"""

# Public alias — used by checker.py when building a preset-driven prompt
SECTION_INSTRUCTIONS = _SECTION_INSTRUCTIONS


def full_check() -> str:
    """Check grammar, spelling, structure, and tone. Return a rewrite."""
    return (
        "You are a professional editor. Read the text in the image carefully.\n"
        "Provide a comprehensive review covering grammar, spelling, structure, and tone.\n\n"
        + _SECTION_INSTRUCTIONS
    )


def grammar_only() -> str:
    """Focus only on grammar issues (sentence structure, tense, subject-verb agreement)."""
    return (
        "You are a professional editor. Read the text in the image carefully.\n"
        "Focus ONLY on grammar issues: sentence structure, tense consistency, "
        "subject-verb agreement, and punctuation.\n\n"
        "## GRAMMAR\n"
        "List each grammar issue on a new line, prefixed with a dash.\n\n"
        "## SPELLING\n"
        "- None found.\n\n"
        "## STRUCTURE\n"
        "- None found.\n\n"
        "## TONE\n"
        "- None found.\n\n"
        "## REWRITE\n"
        "Provide a corrected version fixing grammar issues only.\n\n"
        'If there are no grammar issues, write "None found." under GRAMMAR.'
    )


def spelling_only() -> str:
    """Focus only on spelling errors (typos, misspellings, homophone errors)."""
    return (
        "You are a professional editor. Read the text in the image carefully.\n"
        "Focus ONLY on spelling errors: typos, misspellings, and homophone mistakes.\n\n"
        "## GRAMMAR\n"
        "- None found.\n\n"
        "## SPELLING\n"
        "List each spelling error on a new line, prefixed with a dash.\n\n"
        "## STRUCTURE\n"
        "- None found.\n\n"
        "## TONE\n"
        "- None found.\n\n"
        "## REWRITE\n"
        "Provide a corrected version fixing spelling errors only.\n\n"
        'If there are no spelling errors, write "None found." under SPELLING.'
    )


def structure_only() -> str:
    """Focus only on paragraph flow, logical order, and transitions."""
    return (
        "You are a professional editor. Read the text in the image carefully.\n"
        "Focus ONLY on structure: paragraph flow, logical ordering, and transition quality.\n\n"
        "## GRAMMAR\n"
        "- None found.\n\n"
        "## SPELLING\n"
        "- None found.\n\n"
        "## STRUCTURE\n"
        "List each structure or flow suggestion on a new line, prefixed with a dash.\n\n"
        "## TONE\n"
        "- None found.\n\n"
        "## REWRITE\n"
        "Provide a rewritten version with improved structure and flow.\n\n"
        'If there are no structure issues, write "None found." under STRUCTURE.'
    )


def tone_only() -> str:
    """Focus only on tone (formality, active/passive voice, word choice)."""
    return (
        "You are a professional editor. Read the text in the image carefully.\n"
        "Focus ONLY on tone: formality level, active vs passive voice, and word choice.\n\n"
        "## GRAMMAR\n"
        "- None found.\n\n"
        "## SPELLING\n"
        "- None found.\n\n"
        "## STRUCTURE\n"
        "- None found.\n\n"
        "## TONE\n"
        "List each tone observation on a new line, prefixed with a dash.\n\n"
        "## REWRITE\n"
        "Provide a rewritten version with improved tone.\n\n"
        'If there are no tone issues, write "None found." under TONE.'
    )
