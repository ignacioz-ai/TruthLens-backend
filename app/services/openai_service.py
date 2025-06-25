from typing import Optional, List, Dict, Any
import logging
import json
from openai import AsyncOpenAI
from ..models.schemas import AnalysisResponse
from ..core.config import settings
from .storage_service import StorageService
from ..models.schemas import PoliticalBias
from ..utils.retriever import search_web
import unicodedata
from ..prompts.analysis_prompts import (
    get_analysis_prompt,
    get_system_prompt,
    get_web_search_instructions,
    get_image_forensics_prompt
)
from ..prompts.chat_prompts import get_chat_system_prompt
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRIGGER_KEYWORDS = [
    # Español
    "veracidad", "verificar", "fuente", "es cierto", "analicemos", "comprobar", "chequear", "buscar en internet",
    # Inglés
    "truth", "verify", "source", "fact check", "fact-check", "check this", "is it true", "analyze", "search online"
]

def normalize(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower())
        if unicodedata.category(c) != 'Mn'
    )

def should_use_web_search(message: str, use_web_search_flag: bool = False) -> bool:
    norm_msg = normalize(message)
    return use_web_search_flag or any(kw in norm_msg for kw in TRIGGER_KEYWORDS)

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            max_retries=2,
            timeout=60.0,
        )
        self.model = settings.OPENAI_MODEL
        self.storage = StorageService()

    async def analyze_text(
        self,
        text: str,
        url: Optional[str] = None,
        title: Optional[str] = None
    ) -> AnalysisResponse:
        # Prepare the prompt
        prompt = get_analysis_prompt(text, url, title)

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
            response_format={ "type": "json_object" }
        )

        # Parse the response
        analysis_text = response.choices[0].message.content
        
        try:
            # Parse the JSON response
            analysis_data = json.loads(analysis_text)

            # Valores por defecto para campos opcionales
            default_article_type = {
                "objective": 0,
                "subjective": 0,
                "speculative": 0,
                "emotive": 0,
                "clickbait": 0
            }
            default_sentiments = {
                "joy": 0,
                "trust": 0,
                "fear": 0,
                "surprise": 0,
                "sadness": 0,
                "disgust": 0,
                "anger": 0,
                "anticipation": 0
            }
            article_type = analysis_data.get("article_type") or default_article_type
            sentiments = analysis_data.get("sentiments") or default_sentiments

            # Validación extra para sentiments
            if not isinstance(sentiments, dict):
                sentiments = default_sentiments

            # Convert the bias string to the corresponding PoliticalBias enum value
            try:
                bias_enum = PoliticalBias(analysis_data["bias"].lower())
            except ValueError:
                bias_enum = PoliticalBias.OTHER

            # Create the analysis response
            analysis_response = AnalysisResponse(
                factual_accuracy=analysis_data["factual_accuracy"],
                bias=bias_enum,
                emotional_tone=analysis_data["emotional_tone"],
                recommendation=analysis_data["recommendation"],
                article_type=article_type,
                sentiments=sentiments,
                analysis_explanation=analysis_data["analysis_explanation"],
                topic=analysis_data.get("topic"),
                frames_detected=analysis_data.get("frames_detected")
            )
            
            # Save article and analysis
            self.storage.save_article(text, analysis_response.dict())
            
            return analysis_response
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            raise Exception(f"Error parsing OpenAI response: {str(e)}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        article_text: Optional[str] = None,
        analysis_result: Optional[Dict] = None,
        use_web_search: bool = False
    ) -> Dict[str, Any]:
        """Chat with the model about an article and its analysis."""
        try:
            # Get current article from storage
            current_article = self.storage.get_current_article()
            
            # Prepare system message with context
            system_message = {
                "role": "system",
                "content": get_chat_system_prompt()
            }

            # Add article context if available
            if article_text and analysis_result:
                # Usar el contexto enviado por el frontend
                system_message["content"] += f"\n\nArticle to analyze:\n{article_text}"
                system_message["content"] += f"\n\nCurrent analysis:\n{json.dumps(analysis_result, indent=2)}"
            elif current_article:
                # Usar el último guardado en cache
                system_message["content"] += f"\n\nArticle to analyze:\n{current_article['text']}"
                if current_article.get('analysis'):
                    system_message["content"] += f"\n\nCurrent analysis:\n{json.dumps(current_article['analysis'], indent=2)}"

            # Get the last user message (multilingual trigger)
            last_user_message = next((msg.content for msg in reversed(messages) if msg.role == "user"), None)
            trigger_web_search = False
            if last_user_message:
                trigger_web_search = should_use_web_search(last_user_message, use_web_search)

            # If web search is requested (by flag or trigger), perform the search and add results to context
            if trigger_web_search:
                try:
                    # Use 10 results if the message is about verifying news (using multilingual trigger)
                    num_results = 10 if any(kw in normalize(last_user_message) for kw in [
                        "veracidad", "verificar", "fact check", "fact-check", "analicemos", "truth", "verify", "fact check", "fact-check", "analyze"
                    ]) else 5
                    logger.info(f"Performing web search with {num_results} results for query: {last_user_message}")
                    search_results = search_web(last_user_message, num_results=num_results)
                    if search_results:
                        system_message["content"] += "\n\nWeb search results (use ONLY these sources):\n"
                        for idx, result in enumerate(search_results, 1):
                            system_message["content"] += f"\n[{idx}] Title: {result['title']}\nSnippet: {result['snippet']}\nURL: {result['url']}\n"
                        system_message["content"] += get_web_search_instructions()
                    else:
                        logger.warning("No search results found")
                except Exception as e:
                    logger.error(f"Error during web search: {str(e)}", exc_info=True)
                    raise Exception(f"Error during web search: {str(e)}")

            # Prepare messages with system context
            filtered_messages = [msg.dict() for msg in messages if msg.role != "system"]
            full_messages = [system_message] + filtered_messages
            logger.info(f"Sending request to OpenAI with {len(full_messages)} messages")

            # Get response from OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.2,
                max_tokens=2000
            )

            return {
                "message": {
                    "role": "assistant",
                    "content": response.choices[0].message.content
                }
            }

        except Exception as e:
            logger.error(f"Error in OpenAI communication: {str(e)}", exc_info=True)
            raise Exception(f"Error in OpenAI communication: {str(e)}")

    async def analyze_with_gpt4(self, original_image: str, spectrum_image: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an image using GPT-4 Vision with the original image, spectrum, and metadata.
        """
        try:
            prompt = get_image_forensics_prompt(metadata)
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in forensic image analysis and AI-generated content detection."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{original_image}"}},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{spectrum_image}"}}
                        ]
                    }
                ],
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            logger.error(f"[ImageAnalysis] Respuesta cruda de OpenAI: {response.choices[0].message.content!r}")
            analysis = json.loads(response.choices[0].message.content)
            return analysis
        except Exception as e:
            raise Exception(f"Error analyzing image with GPT-4: {str(e)}") 