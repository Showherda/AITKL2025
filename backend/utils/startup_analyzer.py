# startup_analyzer.py
import google.generativeai as genai
import json
import os
import re
from dotenv import load_dotenv
from duckduckgo_search import DDGS
import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from typing import Dict, List, Optional, Any

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Configuration & Constants ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# API Retry Parameters
DEFAULT_API_MAX_ATTEMPTS = 3
DEFAULT_API_RETRY_WAIT_MULTIPLIER = 1
DEFAULT_API_RETRY_WAIT_MIN = 2
DEFAULT_API_RETRY_WAIT_MAX = 10

# Search Parameters
DDGS_MAX_NEWS_RESULTS = 7
MAX_ARTICLES_FOR_GEMINI_SUMMARY = 5 # Limit articles sent to Gemini for summary context

# Default Error Responses (used when API calls fail or parsing is unsuccessful)
DEFAULT_SENTIMENT_ERROR: Dict[str, Any] = {"sentiment": "Error", "sentiment_score": 0.0, "reasoning": "API call failed or response unparsable after retries."}
DEFAULT_NEWS_SUMMARY_FALLBACK: Dict[str, Any] = {
    "overall_news_summary": "Could not generate news summary due to API error or unparsable response after retries.",
    "prominent_headlines": [],
}
DEFAULT_CATEGORIZATION_ERROR: Dict[str, Any] = {"primary_category": "Error", "sub_categories": [], "keywords": [], "reason": "API call failed or response unparsable after retries."}
DEFAULT_GROWTH_PREDICTION_ERROR: Dict[str, Any] = {
    "growth_potential_assessment": "Error",
    "key_factors_from_news": [],
    "potential_opportunities_highlighted_by_news": [],
    "potential_risks_or_challenges_from_news": [],
    "overall_outlook_summary_based_on_news": "Prediction failed due to API error or unparsable response after retries."
}

# --- Gemini Model Configuration ---
generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 1, # Kept at 1 for more deterministic JSON output, can be increased for more varied text
    "max_output_tokens": 2048,
    "response_mime_type": "application/json", # Crucial for reliable JSON output
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest", # Ensure this model supports JSON mode well
    generation_config=generation_config,
    safety_settings=safety_settings,
)

# --- Helper Functions ---

def parse_gemini_json_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parses a text response expected to be a JSON string.
    Relies on Gemini's JSON mode but includes fallbacks for common issues.
    """
    try:
        # With JSON mode, response_text should be a clean JSON string.
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSONDecodeError: {e}. Attempting to extract from markdown.")
        # Fallback: try to extract from markdown ```json ... ``` block
        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if match:
            json_str_markdown = match.group(1)
            try:
                logger.info("Successfully extracted JSON from markdown block.")
                return json.loads(json_str_markdown)
            except json.JSONDecodeError as e_markdown:
                logger.error(f"Error decoding JSON from extracted markdown: {e_markdown}\nMarkdown content snippet: {json_str_markdown[:200]}...")
                return None
        logger.error(f"Failed to decode JSON and no markdown block found. Response snippet: {response_text[:500]}...")
        return None
    except Exception as e: # Catch any other unexpected errors during parsing
        logger.error(f"Unexpected error parsing Gemini JSON response: {e}\nResponse snippet: {response_text[:500]}...")
        return None

@retry(
    stop=stop_after_attempt(DEFAULT_API_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=DEFAULT_API_RETRY_WAIT_MULTIPLIER, min=DEFAULT_API_RETRY_WAIT_MIN, max=DEFAULT_API_RETRY_WAIT_MAX),
    reraise=True # Reraise the last exception if all retries fail
)
def _generate_content_with_retry(prompt_parts: List[str]) -> Any: # Returns Gemini Response object
    logger.debug(f"Attempting to generate content with Gemini. Prompt snippet: {str(prompt_parts[0])[:100]}...")
    return model.generate_content(prompt_parts)

def _call_gemini_with_prompt(prompt: str, error_fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to call Gemini, parse JSON, and handle errors with retries."""
    try:
        response = _generate_content_with_retry([prompt]) # Pass prompt as a list
        parsed_data = parse_gemini_json_response(response.text)
        if parsed_data:
            return parsed_data
        
        logger.warning(f"Failed to parse valid JSON data from Gemini. Response text snippet: {response.text[:200]}")
        # Update fallback with specific parsing failure reason
        reason = "Failed to parse Gemini response or response was empty."
        return {**error_fallback, **_get_reason_field(error_fallback, reason)}

    except RetryError as e:
        logger.error(f"Gemini API call failed after {DEFAULT_API_MAX_ATTEMPTS} retries: {e}")
        return error_fallback # error_fallback already contains a generic API failure message
    except Exception as e:
        logger.error(f"Unexpected error during Gemini call: {e}")
        reason = f"Unexpected error: {str(e)}"
        return {**error_fallback, **_get_reason_field(error_fallback, reason)}

def _get_reason_field(fallback_dict: Dict[str, Any], reason_text: str) -> Dict[str, str]:
    """Determines which 'reason' field to update in a fallback dictionary."""
    if "reasoning" in fallback_dict: return {"reasoning": reason_text}
    if "reason" in fallback_dict: return {"reason": reason_text}
    if "overall_news_summary" in fallback_dict: return {"overall_news_summary": reason_text} # For summary
    return {} # No standard reason field found

@retry(
    stop=stop_after_attempt(DEFAULT_API_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=DEFAULT_API_RETRY_WAIT_MULTIPLIER, min=DEFAULT_API_RETRY_WAIT_MIN, max=DEFAULT_API_RETRY_WAIT_MAX),
    reraise=True
)
def _ddgs_news_with_retry(ddgs_instance, keywords: str, max_results: int) -> List[Dict[str, Any]]:
    logger.debug(f"Attempting DDGS news search for keywords: {keywords}")
    # The DDGS library might return a generator, ensure it's converted to list within retry
    search_results = list(ddgs_instance.news(
        keywords=keywords, region='wt-wt', safesearch='moderate', max_results=max_results
    ))
    return search_results

def search_news_mentions(startup_name: str, max_results: int = DDGS_MAX_NEWS_RESULTS) -> List[Dict[str, Any]]:
    logger.info(f"Searching for news about '{startup_name}' (max {max_results} results)...")
    query = f"{startup_name} news OR funding OR launch OR partnership OR product OR innovation"
    articles = []
    try:
        with DDGS() as ddgs:
            search_results = _ddgs_news_with_retry(ddgs, keywords=query, max_results=max_results)
            if search_results:
                for r in search_results:
                    articles.append({
                        "title": r.get('title', 'N/A'),
                        "url": r.get('url', 'N/A'),
                        "source": r.get('source', 'N/A'),
                        "publish_date": r.get('date', 'N/A'),
                        "snippet": r.get('body', 'N/A')
                    })
        logger.info(f"Found {len(articles)} news articles for '{startup_name}'.")
    except RetryError as e:
        logger.error(f"DDGS news search failed for '{startup_name}' after multiple retries: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during news search for '{startup_name}': {e}")
    return articles

def analyze_article_sentiment_with_gemini(article_title: str, article_snippet: str) -> Dict[str, Any]:
    text_to_analyze = f"Title: {article_title}\nSnippet: {article_snippet}".strip()
    if len(text_to_analyze) < 20: # Arbitrary threshold for meaningful text
        return {"sentiment": "Neutral", "sentiment_score": 0.0, "reasoning": "Not enough text for analysis."}

    prompt = f"""
    Analyze the sentiment of the following news article text.
    The sentiment should be one of: "Positive", "Negative", or "Neutral".
    Provide a sentiment_score between -1.0 (very negative) and 1.0 (very positive).
    Respond ONLY with a JSON object with the exact structure: {{"sentiment": "...", "sentiment_score": ...}}

    Article Text:
    ---
    {text_to_analyze}
    ---
    """
    result = _call_gemini_with_prompt(prompt, DEFAULT_SENTIMENT_ERROR.copy())

    # Ensure critical keys are present even if JSON is parsed, otherwise use defaults
    if not ("sentiment" in result and "sentiment_score" in result and isinstance(result["sentiment_score"], (float, int))):
        logger.warning(f"Sentiment analysis response missing required keys or invalid score: {result}")
        return {
            "sentiment": result.get("sentiment", DEFAULT_SENTIMENT_ERROR["sentiment"]),
            "sentiment_score": result.get("sentiment_score", DEFAULT_SENTIMENT_ERROR["sentiment_score"]),
            "reasoning": result.get("reasoning", "Parsed response missing required sentiment/score keys or invalid score type.")
        }
    return result

def perform_sentiment_analysis_for_articles(news_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    logger.info("Performing sentiment analysis on individual news articles...")
    analyzed_articles_details = []
    total_score = 0.0
    valid_articles_count = 0

    for article in news_articles:
        title = article.get('title', 'N/A')
        logger.info(f"  Analyzing sentiment for: {title[:70]}...")
        sentiment_result = analyze_article_sentiment_with_gemini(title, article.get('snippet',''))
        
        analyzed_article = article.copy()
        analyzed_article.update(sentiment_result)
        analyzed_articles_details.append(analyzed_article)

        if sentiment_result.get("sentiment") != "Error" and isinstance(sentiment_result.get("sentiment_score"), (float, int)):
            total_score += sentiment_result["sentiment_score"]
            valid_articles_count += 1
    
    overall_sentiment_label = "Neutral"
    average_sentiment_score = 0.0

    if valid_articles_count > 0:
        average_sentiment_score = round(total_score / valid_articles_count, 2)
        if average_sentiment_score > 0.2: overall_sentiment_label = "Positive"
        elif average_sentiment_score < -0.2: overall_sentiment_label = "Negative"

    logger.info(f"Overall news sentiment from articles: {overall_sentiment_label} (Avg Score: {average_sentiment_score})")
    return {
        "detailed_articles": analyzed_articles_details,
        "overall_calculated_sentiment": overall_sentiment_label,
        "average_sentiment_score": average_sentiment_score,
        "analyzed_article_count": valid_articles_count
    }

def summarize_news_and_extract_headlines_with_gemini(
    analyzed_articles_data: Dict[str, Any], startup_name: str
) -> Dict[str, Any]:
    logger.info("Summarizing news and extracting headlines with Gemini...")
    
    articles_for_summary = analyzed_articles_data.get("detailed_articles", [])
    base_result = { # Structure for merging results or fallbacks
        "overall_news_sentiment": analyzed_articles_data.get("overall_calculated_sentiment", "Neutral"),
        "average_sentiment_score": analyzed_articles_data.get("average_sentiment_score", 0.0),
        "analyzed_article_count": analyzed_articles_data.get("analyzed_article_count", 0),
        "detailed_articles_for_reference": articles_for_summary
    }

    if not articles_for_summary:
        logger.warning("No news articles found or provided for summary.")
        return {
            **DEFAULT_NEWS_SUMMARY_FALLBACK,
            "overall_news_summary": "No news articles found or provided for summary.",
            **base_result
        }

    news_context = f"Recent news mentions for startup '{startup_name}':\n"
    for i, article in enumerate(articles_for_summary[:MAX_ARTICLES_FOR_GEMINI_SUMMARY]):
        news_context += (
            f"Article {i+1}:\n"
            f"  Title: {article.get('title', 'N/A')}\n"
            f"  Snippet: {article.get('snippet', 'N/A')}\n"
            f"  Sentiment: {article.get('sentiment', 'N/A')} (Score: {article.get('sentiment_score', 0.0)})\n\n"
        )

    prompt = f"""
    Based on the following news article information for the startup '{startup_name}', provide:
    1. An `overall_news_summary` (3-5 sentences) of the key information and themes from these articles.
    2. A list of 2-3 `prominent_headlines` (exact titles from the provided articles if they are representative, or slightly rephrased for prominence).

    Respond ONLY with a JSON object in the format:
    {{
      "overall_news_summary": "...",
      "prominent_headlines": ["Headline 1...", "Headline 2..."]
    }}

    News Article Information:
    ---
    {news_context}
    ---
    """
    summary_data = _call_gemini_with_prompt(prompt, DEFAULT_NEWS_SUMMARY_FALLBACK.copy())
    
    # Ensure critical keys, even if JSON is parsed
    if not ("overall_news_summary" in summary_data and "prominent_headlines" in summary_data):
        logger.warning(f"News summary response missing required keys: {summary_data}")
        final_summary = DEFAULT_NEWS_SUMMARY_FALLBACK.copy()
        if "overall_news_summary" not in summary_data:
             final_summary["overall_news_summary"] = "Summary not generated or keys missing."
        else: # Prominent headlines might be missing
            final_summary["overall_news_summary"] = summary_data.get("overall_news_summary", "Summary key present but value missing.")
        final_summary["prominent_headlines"] = summary_data.get("prominent_headlines", [])

    else:
        final_summary = summary_data

    return {**final_summary, **base_result}


def categorize_startup_with_gemini(startup_info: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Categorizing startup '{startup_info.get('name', 'N/A')}' with Gemini...")
    context = (
        f"Startup Name: {startup_info.get('name', 'N/A')}\n"
        f"Industry: {startup_info.get('industry', 'N/A')}\n"
        f"Description: {startup_info.get('description_short', 'N/A')}\n"
        f"Long Description: {startup_info.get('description_long', '')}"
    )
    prompt = f"""
    Based on the following startup information, provide:
    1. A `primary_category` (e.g., "SaaS", "FinTech", "AI Software").
    2. A list of 2-4 `sub_categories`.
    3. A list of 3-5 relevant `keywords`.

    Respond ONLY with a JSON object with the exact structure:
    {{
      "primary_category": "...",
      "sub_categories": ["...", "..."],
      "keywords": ["...", "..."]
    }}

    Startup Information:
    ---
    {context}
    ---
    """
    result = _call_gemini_with_prompt(prompt, DEFAULT_CATEGORIZATION_ERROR.copy())
    if "primary_category" in result and result["primary_category"] != "Error":
         logger.info(f"Gemini Primary Category: {result.get('primary_category')}")
    return result

def predict_growth_based_on_news_with_gemini(
    startup_info: Dict[str, Any], news_analysis_summary: Dict[str, Any], categorization: Dict[str, Any]
) -> Dict[str, Any]:
    logger.info(f"Predicting startup growth for '{startup_info.get('name', 'N/A')}' (news-focused) with Gemini...")
    
    context = (
        f"Startup Profile:\n"
        f"  Name: {startup_info.get('name', 'N/A')}\n"
        f"  Industry: {startup_info.get('industry', 'N/A')}\n"
        f"  Description: {startup_info.get('description_short', 'N/A')}\n"
        f"  Founded: {startup_info.get('founded_year', 'N/A')}\n"
        f"  Funding Stage: {startup_info.get('funding_stage', 'N/A')}\n\n"
        f"Automated Categorization:\n"
        f"  Primary: {categorization.get('primary_category', 'N/A')}\n"
        f"  Sub-categories: {', '.join(categorization.get('sub_categories', []))}\n\n"
        f"News Analysis & Summary:\n"
        f"  Overall News Sentiment: {news_analysis_summary.get('overall_news_sentiment', 'N/A')} "
        f"(Avg Score: {news_analysis_summary.get('average_sentiment_score', 'N/A')})\n"
        f"  Prominent Headlines: {', '.join(news_analysis_summary.get('prominent_headlines', ['N/A']))}\n"
        f"  News Summary: {news_analysis_summary.get('overall_news_summary', 'N/A')}\n"
    )

    prompt = f"""
    Based on the startup's profile, its recent news coverage summary, and its categorization, provide a predictive analysis for its growth.
    Focus particularly on how the news sentiment and content might influence its trajectory.

    Respond ONLY with a JSON object with the following exact structure:
    {{
      "growth_potential_assessment": "High/Medium/Low/Uncertain (based on current info)",
      "key_factors_from_news": ["Factor 1 from news influencing outlook...", "Factor 2..."],
      "potential_opportunities_highlighted_by_news": ["Opportunity 1...", "Opportunity 2..."],
      "potential_risks_or_challenges_from_news": ["Risk 1 based on news...", "Challenge 2..."],
      "overall_outlook_summary_based_on_news": "A concise (2-4 sentences) summary of the startup's growth outlook, strongly considering the news analysis."
    }}

    Comprehensive Information:
    ---
    {context}
    ---
    """
    result = _call_gemini_with_prompt(prompt, DEFAULT_GROWTH_PREDICTION_ERROR.copy())
    if "growth_potential_assessment" in result and result["growth_potential_assessment"] != "Error":
        logger.info(f"Gemini Growth Potential Assessment: {result.get('growth_potential_assessment')}")
    return result

# --- Main Analysis Function ---
def analyze_startup(startup_info_json: str) -> str:
    try:
        startup_info = json.loads(startup_info_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid input JSON: {e}")
        return json.dumps({"error": f"Invalid input JSON: {str(e)}"}, indent=2)

    startup_name = startup_info.get("name")
    if not startup_name:
        logger.error("Startup 'name' is a required field in input JSON.")
        return json.dumps({"error": "Startup 'name' is a required field."}, indent=2)

    logger.info(f"Starting focused analysis for: {startup_name}")

    raw_news_articles = search_news_mentions(startup_name, max_results=DDGS_MAX_NEWS_RESULTS)
    individual_articles_sentiment_data = perform_sentiment_analysis_for_articles(raw_news_articles)
    
    news_analysis_and_summary_result = summarize_news_and_extract_headlines_with_gemini(
        individual_articles_sentiment_data,
        startup_name
    )

    categorization_result = categorize_startup_with_gemini(startup_info)
    growth_prediction_result = predict_growth_based_on_news_with_gemini(
        startup_info,
        news_analysis_and_summary_result,
        categorization_result
    )

    output_data = {
        "startup_info_processed": startup_info,
        "news_analysis_and_summary": news_analysis_and_summary_result,
        "automated_categorization": categorization_result,
        "predictive_growth_analytics": growth_prediction_result,
        "analysis_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    logger.info(f"Focused analysis complete for: {startup_name}")
    return json.dumps(output_data, indent=2)

# --- Example Usage ---
if __name__ == "__main__":
    example_startup_json = """
    {
      "name": "Aether BioSystems",
      "website": "https://aetherbio.example.com",
      "industry": "Biotechnology",
      "description_short": "Pioneering synthetic biology for sustainable chemical production.",
      "description_long": "Aether BioSystems leverages CRISPR and AI-driven metabolic engineering to design microorganisms that can produce high-value chemicals from renewable feedstocks. Our mission is to decarbonize the chemical industry and create a circular bioeconomy. We have recently announced a major partnership with a leading chemical company and secured Series B funding.",
      "location_city": "Boston",
      "location_country": "USA",
      "founded_year": 2019,
      "funding_stage": "Series B"
    }
    """
    logger.info("--- Analyzing Aether BioSystems (Focused Output) ---")
    analysis_result_json = analyze_startup(example_startup_json)
    
    # Using logger for final output as well, or print if preferred for CLI direct output
    print("\n--- FINAL FOCUSED JSON OUTPUT (Aether BioSystems) ---") # print for final result visibility
    print(analysis_result_json)

    output_filename = "aether_biosystems_focused_analysis.json"
    try:
        with open(output_filename, "w") as f:
            f.write(analysis_result_json)
        logger.info(f"Results saved to {output_filename}")
    except IOError as e:
        logger.error(f"Failed to write results to {output_filename}: {e}")

    # Example with a startup that might have fewer/no news results
    example_no_news_startup_json = """
    {
        "name": "MyFictionalStartupXYZ123NoNews",
        "industry": "Stealth",
        "description_short": "A very new and stealthy startup."
    }
    """
    logger.info("\n--- Analyzing MyFictionalStartupXYZ123NoNews (Focused Output) ---")
    analysis_no_news_result_json = analyze_startup(example_no_news_startup_json)
    print("\n--- FINAL FOCUSED JSON OUTPUT (MyFictionalStartupXYZ123NoNews) ---")
    print(analysis_no_news_result_json)
    output_filename_no_news = "fictional_startup_no_news_analysis.json"
    try:
        with open(output_filename_no_news, "w") as f:
            f.write(analysis_no_news_result_json)
        logger.info(f"Results saved to {output_filename_no_news}")
    except IOError as e:
        logger.error(f"Failed to write results to {output_filename_no_news}: {e}")