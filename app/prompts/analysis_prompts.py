from typing import Optional
import json

def get_analysis_prompt(text: str, url: Optional[str] = None, title: Optional[str] = None) -> str:
    """
    Generate the main analysis prompt for text analysis.
    
    Args:
        text: The text to analyze
        url: Optional URL of the article
        title: Optional title of the article
        
    Returns:
        str: The formatted prompt
    """
    context = f"Text to analyze:\n{text}\n"
    if url:
        context += f"\nURL: {url}\n"
    if title:
        context += f"\nTitle: {title}\n"

    return f"""Analyze the following text for factual accuracy, political bias, emotional tone, and article structure. Base your evaluation on established variables and constructs from DOCA (Database of Variables for Content Analysis), especially those used in automated content analysis of journalistic texts.

{context}

Identify the main topic of the article from the following list and return it as the field "topic": politics, economy, health, technology, culture, sports, environment, crime, international, education, other.

Based on the article, identify any applicable framing categories used to present the topic. Choose from: crisis, conflict, human_interest, responsibility, morality, solution, economic_consequences, security, none. Return them as an array in the field "frames_detected".

Return your analysis as a valid JSON object with ALL the following fields, even if some values are zero, empty, or not applicable. Do NOT omit any field. Use the exact structure and field names below:

{{
    "factual_accuracy": <integer from 0-100>,
    "bias": <one of: \"neutral\", \"center-left\", \"left-leaning\", \"center-right\", \"right-leaning\", \"anti-government\", \"pro-government\", \"other\">,
    "emotional_tone": <one of: \"neutral\", \"positive\", \"negative\", \"mixed\">,
    "recommendation": <string>,
    "topic": <one of: \"politics\", \"economy\", \"health\", \"technology\", \"culture\", \"sports\", \"environment\", \"crime\", \"international\", \"education\", \"other\">,
    "frames_detected": [<any of: \"crisis\", \"conflict\", \"human_interest\", \"responsibility\", \"morality\", \"solution\", \"economic_consequences\", \"security\">],
    "article_type": {{
        "objective": <float 0-1>,
        "subjective": <float 0-1>,
        "speculative": <float 0-1>,
        "emotive": <float 0-1>,
        "clickbait": <float 0-1>
    }},
    "sentiments": {{
        "joy": <float 0-1>,
        "trust": <float 0-1>,
        "fear": <float 0-1>,
        "surprise": <float 0-1>,
        "sadness": <float 0-1>,
        "disgust": <float 0-1>,
        "anger": <float 0-1>,
        "anticipation": <float 0-1>
    }},
    "analysis_explanation": {{
        "factual_accuracy": {{
            "score": <integer 0-100>,
            "key_indicators": <string>,
            "examples_from_text": <string>,
            "weight_of_factors": <string>,
            "comparison_with_similar_content": <string>
        }},
        "bias": {{
            "classification": <string>,
            "language_patterns": <string>,
            "examples_of_bias": <string>,
            "context_and_implications": <string>,
            "effect_on_message": <string>
        }},
        "emotional_tone": {{
            "classification": <string>,
            "emotional_language_patterns": <string>,
            "examples_of_emotional_language": <string>,
            "impact_on_message": <string>,
            "effect_on_credibility": <string>
        }},
        "recommendation": {{
            "text": <string>,
            "key_factors": <string>,
            "specific_concerns": <string>,
            "relation_to_other_classifications": <string>
        }}
    }}
}}

IMPORTANT: The field "sentiments" MUST always be a JSON object with ALL of the following keys: "joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation". Do not use a string or array. If a value is not present, use 0.
If you do not have data for a field, use 0 for numbers, "" for strings, and [] for arrays. Do NOT omit any field. Return only the JSON object, nothing else.
"""

def get_system_prompt() -> str:
    """
    Get the system prompt for the analysis.
    
    Returns:
        str: The system prompt
    """
    return """You are an expert in news verification and objectivity analysis. Use clear and accessible language for the general public. For bias analysis, use EXACTLY one of the specified classifications."""

def get_web_search_instructions() -> str:
    """
    Get the instructions for web search results.
    
    Returns:
        str: The web search instructions
    """
    return """Instructions: You MUST base your answer ONLY on the web search results above. 
For every claim, cite the source with its URL in parentheses. 
At the end of your answer, list all the URLs you checked as 'Sources checked:'. 
If none of the sources are relevant, reply: 'I couldn't find any reliable sources to verify that information. If you want, you can try rephrasing your question, provide more details, or ask about a related topic!' 
Do NOT use your own knowledge or make up information. Respond in the same language as the user."""

def get_image_forensics_prompt(metadata: dict) -> str:
    """
    Prompt para análisis forense de imágenes IA con contexto, instrucciones y formato de salida JSON.
    """
    return f"""You are an expert in forensic image analysis and AI-generated content detection.\n\nYou will receive three elements:\n\n1. The original image that needs to be evaluated.\n2. The corresponding frequency spectrum (FFT) of the image, showing the distribution of spatial frequencies.\n3. Metadata extracted from the original image (EXIF), such as camera model, software used, creation time, and GPS data.\n\nYour task is to assess whether the original image was generated by an AI model, using all three sources of information.\n\n🧠 CONTEXT — Known characteristics of AI-generated images in 2025 (e.g., from models like Sora, Midjourney v6, Imagen 3):\n\n— VISUAL CLUES:\n• Impossibly clean or symmetrical faces  \n• Uniform blur or depth of field  \n• Inconsistent lighting between subject and background  \n• Hands, fingers or ears with unusual shapes  \n• Overly smooth or plastic-looking materials  \n• Lack of realistic imperfections  \n\n— SPECTRAL CLUES:\n• Radial or axial symmetry in the frequency map  \n• Grid patterns or diagonal frequency bands  \n• Localized energy clusters or unnatural periodicity  \n• Lack of natural high-frequency noise or chaotic texture  \n\n— METADATA CLUES:\n• Absence of camera model, GPS info, or timestamp  \n• Presence of known AI tools in the \"Software\" field  \n• Recently generated timestamp without user device info  \n• Conflict between metadata and visual content (e.g., "Nikon" but image looks synthetic)\n\n🧪 Analyze all sources and respond in this exact JSON format:\n\n{{\n  \"ai_probability\": [0-100],\n  \"visual_clues\": [\"list of key visual observations\"],\n  \"spectral_clues\": [\"list of frequency-based anomalies\"],\n  \"metadata_clues\": [\"list of anomalies or suspicious fields in metadata\"],\n  \"verdict\": \"Likely AI-generated\" or \"Likely real\",\n  \"justification\": \"Short explanation referencing all three elements\",\n  \"recommendation\": \"Advice for the user on how to interpret or verify this image\"\n}}\n\n⚠️ Be careful. If the evidence is weak or mixed, reflect that uncertainty in your probability and reasoning.\n\nIMPORTANT: Your response MUST be ONLY the JSON object, with no explanation, no text before or after, and no questions.\n\nHere is the metadata (JSON):\n{json.dumps(metadata, ensure_ascii=False)}\n""" 