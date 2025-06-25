from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class PoliticalBias(str, Enum):
    NEUTRAL = "neutral"
    CENTER_LEFT = "center-left"
    LEFT_LEANING = "left-leaning"
    CENTER_RIGHT = "center-right"
    RIGHT_LEANING = "right-leaning"
    ANTI_GOVERNMENT = "anti-government"
    PRO_GOVERNMENT = "pro-government"
    OTHER = "other"

class AnalysisRequest(BaseModel):
    """
    Request model for article analysis containing the text to analyze.
    
    Attributes:
        text: The article text to be analyzed
        url: Optional URL of the article
        title: Optional title of the article
    """
    text: str = Field(..., min_length=1)
    url: Optional[str] = Field(None, description="Optional URL of the article")
    title: Optional[str] = Field(None, description="Optional title of the article")

class AnalysisResponse(BaseModel):
    """
    Response model for article analysis containing factual accuracy, bias assessment,
    emotional tone, and detailed analysis components.
    
    Attributes:
        factual_accuracy: Score from 0-100 indicating the factual accuracy of the article
        bias: String describing the detected bias in the article
        emotional_tone: String describing the emotional tone of the article
        recommendation: String containing recommendations for the reader
        analysis_explanation: Optional detailed breakdown of the analysis
        article_type: Optional classification of the article type with confidence scores
        sentiments: Optional sentiment analysis scores for different aspects
        topic: Main topic of the article (DOCA)
        frames_detected: List of detected frames (DOCA)
    """
    factual_accuracy: int = Field(..., ge=0, le=100)
    bias: str
    emotional_tone: str
    recommendation: str
    analysis_explanation: Optional[Dict[str, Any]] = Field(default=None, description="Detailed analysis explanation")
    article_type: Optional[Dict[str, float]] = None
    sentiments: Optional[Dict[str, float]] = None
    topic: Optional[str] = Field(default=None, description="Main topic of the article (DOCA)")
    frames_detected: Optional[List[str]] = Field(default=None, description="List of detected frames (DOCA)")

class ChatMessage(BaseModel):
    """
    Model for chat messages.
    
    Attributes:
        role: The role of the message sender (user or assistant)
        content: The content of the message
    """
    role: str
    content: str

class ChatRequest(BaseModel):
    """
    Request model for chat interactions containing the user message,
    original text, and previous analysis.
    
    Attributes:
        messages: List of chat messages
        article_text: Optional original article text
        analysis_result: Optional previous analysis results
        use_web_search: Whether to use web search for answering
    """
    messages: List[ChatMessage]
    article_text: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    use_web_search: Optional[bool] = Field(default=False, description="Whether to use web search for answering the question")

class ChatResponse(BaseModel):
    """
    Response model for chat interactions containing the AI's response.
    
    Attributes:
        message: The AI's response message
    """
    message: ChatMessage

class TranslationRequest(BaseModel):
    """
    Request model for translation containing the text to translate,
    source language, target language, and translation mode.
    
    Attributes:
        text: The text to be translated
        source_language: Two-letter code for the source language
        target_language: Two-letter code for the target language
        translation_mode: The style or approach to use for translation
    """
    text: str = Field(..., min_length=1)
    source_language: str = Field(..., min_length=2, max_length=2)
    target_language: str = Field(..., min_length=2, max_length=2)
    translation_mode: str = Field(..., description="Mode of translation (literal, idiomatic, academic, etc.)")

class TranslationResponse(BaseModel):
    """
    Response model for translation containing the translated text and metadata.
    
    Attributes:
        translated_text: The translated version of the input text
        source_language: The original language code
        target_language: The target language code
        translation_mode: The translation style that was used
    """
    translated_text: str
    source_language: str
    target_language: str
    translation_mode: str 