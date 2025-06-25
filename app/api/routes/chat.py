from fastapi import APIRouter, HTTPException, Depends, Request
from ...models.schemas import ChatRequest, ChatResponse
from ...services.openai_service import OpenAIService
from ...core.config import settings
import logging
from typing import List
from slowapi import Limiter
from slowapi.util import get_remote_address

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router and services
router = APIRouter()
openai_service = OpenAIService()
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Chat with the AI assistant",
    description="Engage in a conversation with the AI assistant about news analysis and bias detection. Optionally use web search for fact verification."
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    limiter: Limiter = Depends(lambda: limiter)
) -> ChatResponse:
    """
    Process a chat request and return the AI's response.
    
    Args:
        request: The HTTP request object (required for slowapi)
        body: The chat request containing the conversation messages
        limiter: Rate limiter instance
        
    Returns:
        ChatResponse: The AI's response to the conversation
        
    Raises:
        HTTPException: If the chat request fails or rate limit is exceeded
    """
    try:
        logger.info("Processing chat request")
        
        # Validate OpenAI API key
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key is not configured"
            )
        
        # Validate messages
        if not body.messages:
            raise HTTPException(
                status_code=400,
                detail="No messages provided in the request"
            )
        
        # Process chat request
        try:
            response = await openai_service.chat(
                messages=body.messages,
                article_text=body.article_text,
                analysis_result=body.analysis_result,
                use_web_search=body.use_web_search
            )
            
            logger.info("Chat request processed successfully")
            return response
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing chat request: {str(e)}"
            )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        ) 