# app.py
import streamlit as st
import json

try:
    from startup_analyzer import analyze_startup, GEMINI_API_KEY
except ImportError:
    st.error("Error: Could not import 'analyze_startup' from 'startup_analyzer.py'. "
             "Make sure the file is in the same directory and has no syntax errors.")
    st.stop()

st.set_page_config(page_title="Focused Startup Analyzer", layout="wide")
st.title("🎯 Focused AI Startup Analyzer")
st.markdown("Enter startup info to get a focused analysis on: News Summary & Sentiment, Categorization, and News-driven Growth Prediction.")

if not GEMINI_API_KEY:
    st.error("🔴 GEMINI_API_KEY not found. Please ensure it's set in your .env file.")
    st.stop()
else:
    st.sidebar.success("✅ Gemini API Key Loaded")

st.sidebar.header("About")
st.sidebar.info(
    "This demo uses Google's Gemini API for focused analysis. "
    "Results are AI-generated and for illustrative purposes."
)

st.header("Enter Startup Information")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Startup Name*", placeholder="e.g., Aether BioSystems")
    website = st.text_input("Website", placeholder="e.g., https://aetherbio.example.com")
    industry = st.text_input("Industry*", placeholder="e.g., Biotechnology")
    founded_year = st.number_input("Founded Year", min_value=1900, max_value=2025, value=2022, step=1)
    
with col2:
    funding_stages = ["N/A", "Pre-seed", "Seed", "Series A", "Series B", "Series C", "Series D+", "Acquired", "IPO", "Other"]
    funding_stage = st.selectbox("Funding Stage", options=funding_stages, index=0)
    location_city = st.text_input("Location City", placeholder="e.g., Boston")
    location_country = st.text_input("Location Country", placeholder="e.g., USA")

description_short = st.text_area("Short Description* (1-2 sentences)", height=100, placeholder="e.g., Pioneering synthetic biology...")
description_long = st.text_area("Long Description (optional)", height=150, placeholder="More details about mission, tech...")

# Removed optional Key People and Competitors for simplicity, can be added back if needed

if st.button("Analyze Startup (Focused) 🔍", type="primary", use_container_width=True):
    if not name or not industry or not description_short:
        st.error("Startup Name, Industry, and Short Description are required fields.")
    else:
        startup_data = {
            "name": name, "website": website, "industry": industry,
            "description_short": description_short, "description_long": description_long,
            "location_city": location_city, "location_country": location_country,
            "founded_year": founded_year,
            "funding_stage": funding_stage if funding_stage != "N/A" else None,
            # "key_people": [], # Add back if re-enabling input
            # "competitors": []  # Add back if re-enabling input
        }
        startup_info_json_str = json.dumps(startup_data)

        with st.spinner("🤖 AI is performing focused analysis... Please wait..."):
            try:
                st.write("--- Input Sent to Analyzer ---")
                st.json(startup_data)

                analysis_result_json_str = analyze_startup(startup_info_json_str)
                analysis_result = json.loads(analysis_result_json_str)

                st.success("🎉 Focused Analysis Complete!")
                st.balloons()

                st.header("📊 Focused Analysis Results")

                if "error" in analysis_result:
                    st.error(f"Analysis Error: {analysis_result['error']}")
                else:
                    # 1. News Analysis and Summary
                    st.subheader("📰 News Analysis & Summary")
                    if "news_analysis_and_summary" in analysis_result:
                        news_data = analysis_result["news_analysis_and_summary"]
                        st.markdown(f"**Overall News Sentiment:** {news_data.get('overall_news_sentiment', 'N/A')} "
                                    f"(Avg. Score: {news_data.get('average_sentiment_score', 0.0):.2f} from "
                                    f"{news_data.get('analyzed_article_count',0)} articles)")
                        
                        st.markdown("**Prominent Headlines:**")
                        if news_data.get("prominent_headlines"):
                            for headline in news_data["prominent_headlines"]:
                                st.markdown(f"- {headline}")
                        else:
                            st.write("No prominent headlines extracted.")
                        
                        st.markdown("**Overall News Summary:**")
                        st.write(news_data.get('overall_news_summary', 'No summary available.'))

                        with st.expander("View Detailed Articles & Individual Sentiments", expanded=False):
                            detailed_articles = news_data.get("detailed_articles_for_reference", [])
                            if detailed_articles:
                                for article in detailed_articles:
                                    st.markdown(f"""
                                    **{article.get('title', 'No Title')}**
                                    * Source: {article.get('source', 'N/A')} ({article.get('publish_date', 'N/A')})
                                    * Sentiment: {article.get('sentiment', 'N/A')} (Score: {article.get('sentiment_score', 'N/A'):.2f})
                                    * [Link]({article.get('url', '#')})
                                    ---
                                    """)
                            else:
                                st.write("No detailed articles found or analyzed.")
                    else:
                        st.warning("News analysis and summary data not found.")

                    # 2. Automated Categorization
                    st.subheader("🏷️ Automated Categorization")
                    if "automated_categorization" in analysis_result:
                        cat_data = analysis_result["automated_categorization"]
                        if cat_data.get("primary_category") != "Error":
                            st.markdown(f"**Primary Category:** {cat_data.get('primary_category', 'N/A')}")
                            st.markdown(f"**Sub-Categories:** {', '.join(cat_data.get('sub_categories', []))}")
                            st.markdown(f"**Keywords:** {', '.join(cat_data.get('keywords', []))}")
                        else:
                            st.warning(f"Categorization failed: {cat_data.get('reason', 'Unknown error')}")
                    else:
                        st.warning("Automated categorization data not found.")

                    # 3. Predictive Growth Analytics (News-Focused)
                    st.subheader("📈 Predictive Growth Analytics (News-Focused)")
                    if "predictive_growth_analytics" in analysis_result:
                        growth_data = analysis_result["predictive_growth_analytics"]
                        if growth_data.get("growth_potential_assessment") != "Error":
                            st.markdown(f"**Growth Potential Assessment:** {growth_data.get('growth_potential_assessment', 'N/A')}")
                            
                            st.markdown("**Key Factors from News:**")
                            for factor in growth_data.get('key_factors_from_news', []): st.markdown(f"- {factor}")
                            
                            st.markdown("**Potential Opportunities (Highlighted by News):**")
                            for opp in growth_data.get('potential_opportunities_highlighted_by_news', []): st.markdown(f"- {opp}")

                            st.markdown("**Potential Risks/Challenges (from News):**")
                            for risk in growth_data.get('potential_risks_or_challenges_from_news', []): st.markdown(f"- {risk}")

                            st.markdown(f"**Overall Outlook Summary (Based on News):** {growth_data.get('overall_outlook_summary_based_on_news', 'N/A')}")
                        else:
                            st.warning(f"Growth prediction failed: {growth_data.get('overall_outlook_summary_based_on_news', 'Unknown error')}")
                    else:
                        st.warning("Predictive growth analytics data not found.")

                    st.subheader("Raw JSON Output")
                    with st.expander("View Full JSON Response"):
                        st.json(analysis_result)

            except Exception as e:
                st.error(f"An unexpected error occurred in the Streamlit app: {e}")
                st.exception(e)

st.markdown("---")
st.markdown("Focused analysis demo. Powered by Streamlit & Google Gemini.")

# Standard boilerplate to run Streamlit app if script is executed directly
if __name__ == "__main__":
    # This check is to prevent Streamlit from re-running if imported as a module,
    # though for a single file app, it's mostly for conventional structure.
    if (
        "__streamlitmagic__" not in locals()
    ):  # Check if running in a Streamlit "magic" environment
        import streamlit.web.bootstrap

        # Args for bootstrap: filename, is_hello, args, flag_options
        streamlit.web.bootstrap.run(__file__, False, [], {})