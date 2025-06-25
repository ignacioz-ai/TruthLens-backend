"""
Web search prompts module for TruthLens.
Contains all the prompts used for web search and fact verification.
"""

def get_web_search_system_prompt() -> str:
    """
    Get the system prompt for web search interactions.
    
    Returns:
        str: The system prompt for web search
    """
    return """You are a fact-checking assistant specialized in verifying news and information.
Your task is to:
1. Analyze the given text and identify claims that need verification
2. Use web search to find reliable sources that support or contradict these claims
3. Provide a clear and objective analysis of the findings
4. Include relevant quotes and sources to support your analysis
5. Maintain a neutral tone and focus on factual accuracy

Remember to:
- Consider the credibility of sources
- Look for multiple sources to cross-reference information
- Be transparent about what can and cannot be verified
- Highlight any potential biases or limitations in the available information"""

def get_web_search_prompt(text: str, search_results: list) -> str:
    """
    Generate a prompt for analyzing web search results.
    
    Args:
        text: The text to verify
        search_results: List of search results from web search
        
    Returns:
        str: A formatted prompt for analyzing search results
    """
    return f"""Text to verify:
{text}

Search results:
{search_results}

Please analyze the search results and provide:
1. A list of claims from the text that can be verified
2. For each claim:
   - Whether it is supported, contradicted, or partially supported by the search results
   - Relevant quotes from reliable sources
   - Any important context or caveats
3. A summary of the overall factual accuracy of the text

Focus on factual claims and avoid opinion-based analysis.""" 