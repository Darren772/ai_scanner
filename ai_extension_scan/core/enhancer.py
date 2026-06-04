"""
AI Preset Enhancer

This module takes raw, unformatted user preset rules and uses the configured AI provider
to paraphrase and enhance them into a robust system directive.
"""

from api.client import get_provider

def enhance_preset(raw_rules: str) -> str:
    """
    Takes raw user rules and uses the AI to enhance them into a strong system prompt.
    Returns the enhanced rules, or the raw rules if the API call fails.
    """
    if not raw_rules or not raw_rules.strip():
        return ""
        
    prompt = (
        "You are an expert prompt engineer. The user has provided a raw, brief, or poorly phrased "
        "instruction for an AI proofreader. Your task is to rewrite and enhance this instruction "
        "into a highly effective, professional system directive.\n\n"
        "Rules for rewriting:\n"
        "1. Do not change the core intent of the user's rule.\n"
        "2. Make it clear, unambiguous, and commanding.\n"
        "3. Output ONLY the enhanced rule block, nothing else. No introductions, no quotes.\n\n"
        "USER'S RAW RULE:\n"
        f"{raw_rules.strip()}"
    )
    
    try:
        provider = get_provider()
        raw_response = provider.send("", prompt)
        
        # Clean up any potential markdown formatting the AI might add
        enhanced = raw_response.strip()
        if enhanced.startswith("```"):
            lines = enhanced.split("\n")
            if len(lines) >= 2:
                # Remove first and last line if they are markdown ticks
                if lines[-1].strip() == "```":
                    enhanced = "\n".join(lines[1:-1])
                else:
                    enhanced = "\n".join(lines[1:])
                    
        return enhanced.strip()
    except Exception as e:
        # If the enhancement fails (e.g. network error, or missing API key), fallback to the raw rules
        print(f"Failed to enhance preset: {e}")
        return raw_rules
