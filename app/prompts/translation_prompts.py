"""
Translation prompts module for TruthLens.
Contains all the prompts and constants used for text translation.
"""

from typing import Dict

# Dictionary defining different translation styles and their characteristics
STYLE_DEFINITIONS: Dict[str, str] = {
    "literal": "literal — translate word-for-word, preserving original grammar and structure",
    "idiomatic": "idiomatic — use natural expressions and fluent language appropriate for the target audience",
    "academic": "academic — use formal tone and structured language suitable for research or scholarly writing",
    "legal": "legal — use precise, formal language appropriate for contracts or official legal documents",
    "technical": "technical — use accurate and concise terminology for scientific or technical content",
    "plain_language": "plain — simplify the language for clarity and accessibility to the general public",
    "journalistic": "journalistic — use a professional tone as used in news reports or media articles",
    "creative": "creative — preserve artistic style, tone, metaphors, and emotional depth"
}

def get_translation_prompt(style: str, target_lang: str, text: str) -> str:
    """
    Generate a translation prompt for the selected style and target language.
    
    Args:
        style: The translation style to use (must be one of the keys in STYLE_DEFINITIONS)
        target_lang: The target language code (e.g., 'en', 'es', 'fr')
        text: The text to be translated
        
    Returns:
        str: A formatted prompt for the translation model
        
    Raises:
        ValueError: If the provided style is not valid
    """
    if style not in STYLE_DEFINITIONS:
        raise ValueError(f"Invalid translation style: {style}")
        
    return (
        "You are a professional translator.\n\n"
        f"Translate the following text from its original language into {target_lang}.\n\n"
        f"Use the following style: {STYLE_DEFINITIONS[style]}.\n\n"
        "Your goal is to preserve the intended meaning while adapting the tone, terminology, and structure to match the selected style.\n\n"
        "Do not return explanations, comments, or the original text — only return the final translated version.\n\n"
        f"Text:\n{text}"
    )

def get_translation_system_prompt() -> str:
    """
    Get the system prompt for translation.
    
    Returns:
        str: The system prompt for translation tasks
    """
    return "You are a professional translator with expertise in multiple languages and translation styles." 