"""
TruthLens prompts package.
This package contains all the prompts used in the application.
"""

from .analysis_prompts import get_analysis_prompt, get_image_forensics_prompt
from .translation_prompts import get_translation_prompt, get_translation_system_prompt
from .chat_prompts import get_chat_system_prompt, get_chat_analysis_prompt
from .web_search_prompts import get_web_search_system_prompt, get_web_search_prompt

__all__ = [
    'get_analysis_prompt',
    'get_image_forensics_prompt',
    'get_translation_prompt',
    'get_translation_system_prompt',
    'get_chat_system_prompt',
    'get_chat_analysis_prompt',
    'get_web_search_system_prompt',
    'get_web_search_prompt'
] 