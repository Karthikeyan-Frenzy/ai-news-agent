import os
import json
import requests
import smtplib
import feedparser

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================================================
# CONFIG
# =========================================================

GMAIL = os.environ["GMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# =========================================================
# OUTPUT CONFIG
# =========================================================

MAX_FRONTIER = 1
MAX_GLOBAL = 2
MAX_INDIA = 2

# =========================================================
# FRONTIER AI LABS
# =========================================================

FRONTIER_FEEDS = [
    "https://openai.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed/"
]

# =========================================================
# GLOBAL AI NEWS
# =========================================================

GLOBAL_RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/"
]

# =========================================================
# INDIA AI NEWS
# =========================================================

INDIA_RSS_FEEDS = [
    "https://analyticsindiamag.com/feed/",
    "https://inc42.com/feed/",
    "https://entrackr.com/feed/",
    "https://yourstory.com/feed/",
    "https://www.moneycontrol.com/rss/technology.xml"
]

# =========================================================
# COMMUNITY SOURCES
# =========================================================

SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA",
    "artificial"
]

# =========================================================
# FILTERING
# =========================================================

AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "llm",
    "gpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "deepseek",
    "mistral",
    "copilot",
    "agent",
    "agents",
    "rag",
    "automation",
    "nvidia",
    "startup",
    "funding",
    "inference",
    "reasoning"
]

FRONTIER_AI_KEYWORDS = [
    "openai",
    "chatgpt",
    "gpt",
    "anthropic",
    "claude",
    "gemini",
    "deepmind",
    "meta ai",
    "llama",
    "xai",
    "grok",
    "deepseek",
    "mistral"
]

BLOCKED_KEYWORDS = [
    "daily roundup",
    "weekly roundup",
    "podcast",
    "webinar",
    "event",
    "live updates",
    "morning briefing",
    "top stories"
]

BAD_SUMMARY_PHRASES = [
    "does not contain",
    "likely includes",
    "may include",
    "unfortunately"
]

# =========================================================
# HELPERS
# =========================================================

def contains_ai_keywords(text):

    text = text.lower()

    return any(
        keyword in text
        for keyword in AI_KEYWORDS
    )

def is_frontier_ai_news(text):

    text = text.lower()

    return any(
        keyword in text
        for keyword in FRONTIER_AI_KEYWORDS
    )

def is_low_quality(text):

    text = text.lower()

    return any(
        keyword in text
        for keyword in BLOCKED_KEYWORDS
    )

def deduplicate_articles(articles):

    seen = set()

    unique = []

    for article in articles:

        title = article["title"].strip().lower()

        if title in seen:
            continue

        seen.add(title)

        unique.append(article)

    return unique

# =========================================================
# RSS FETCHER
# =========================================================

def fetch_rss_articles(
    feeds,
    region,
    category
):

    articles = []

    for url in feeds:

        try:

            feed = feedparser.parse(url)

            source_name = feed.feed.get(
                "title",
                "RSS Feed"
            )

            for entry in feed.entries[:10]:

                title = entry.get("title", "")

                summary = entry.get(
                    "summary",
                    ""
                )

                combined = (
                    f"{title} {summary}"
                )

                if not contains_ai_keywords(combined):
                    continue

                if is_low_quality(combined):
                    continue

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": source_name,
                    "region": region,
                    "category": category
                })

        except Exception as e:

            print(
                f"RSS fetch failed "
                f"for {url}: {e}"
            )

    return articles

# =========================================================
# REDDIT
# =========================================================

def fetch_reddit():

    articles = []

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        for subreddit in SUBREDDITS:

            url = (
                f"https://www.reddit.com/r/"
                f"{subreddit}/hot.json?limit=5"
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            posts = response.json()[
                "data"
            ]["children"]

            for post in posts:

                data = post["data"]

                title = data.get(
                    "title",
                    ""
                )

                if not contains_ai_keywords(title):
                    continue

                if is_low_quality(title):
                    continue

                score = data.get(
                    "score",
                    0
                )

                # only highly trending posts
                if score < 250:
                    continue

                articles.append({
                    "title": title,
                    "summary": data.get(
                        "selftext",
                        ""
                    )[:1200],
                    "link": (
                        "https://reddit.com" +
                        data.get("permalink", "")
                    ),
                    "source": (
                        f"Reddit - r/{subreddit}"
                    ),
                    "region": "global",
                    "category": "community"
                })

    except Exception as e:

        print(f"Reddit error: {e}")

    return articles

# =========================================================
# GITHUB
# =========================================================

def fetch_github():

    articles = []

    try:

        url = (
            "https://api.github.com/"
            "search/repositories"
        )

        params = {
            "q": (
                "llm OR openai OR "
                "agents OR rag OR "
                "anthropic"
            ),
            "sort": "stars",
            "order": "desc",
            "per_page": 5
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        repos = response.json().get(
            "items",
            []
        )

        for repo in repos:

            stars = repo.get(
                "stargazers_count",
                0
            )

            if stars < 5000:
                continue

            title = repo.get(
                "full_name",
                ""
            )

            desc = repo.get(
                "description",
                ""
            )

            articles.append({
                "title": (
                    f"Trending AI Repo: "
                    f"{title}"
                ),
                "summary": desc,
                "link": repo.get(
                    "html_url",
                    ""
                ),
                "source": "GitHub",
                "region": "global",
                "category": "community"
            })

    except Exception as e:

        print(f"GitHub error: {e}")

    return articles

# =========================================================
# ARTICLE SCORING
# =========================================================

def score_article(article):

    prompt = f"""
You are an elite AI news editor.

Your job is to identify IMPORTANT AI NEWS,
not niche technical blogs.

Evaluate this article on:

1. News importance
2. Industry impact
3. Mainstream relevance
4. Enterprise/business impact
5. AI relevance
6. Virality/popularity

Return ONLY valid JSON.

Format:

{{
    "score": number,
    "summary": "<html formatted summary>"
}}

Summary Rules:
- Use HTML only
- NO markdown
- Use <ul>, <li>, <p>, <b>
- Keep concise
- Focus on why people should care
- Mention business or technical impact
- Avoid generic filler

TITLE:
{article['title']}

CONTENT:
{article['summary']}
"""

    try:

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization":
                f"Bearer {GROQ_API_KEY}",
                "Content-Type":
                "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2
            },
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        content = (
            result["choices"][0]
            ["message"]["content"]
        )

        content = (
            content.replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )

        parsed = json.loads(content)

        article["score"] = parsed.get(
            "score",
            0
        )

        # frontier AI boost
        if is_frontier_ai_news(
            article["title"]
        ):
            article["score"] += 10

        # trusted news source boost
        if article["category"] == "frontier":
            article["score"] += 8

        if article["category"] == "global_news":
            article["score"] += 5

        article["summary"] = parsed.get(
            "summary",
            "<p>No summary available.</p>"
        )

        return article

    except Exception as e:

        print(
            f"Scoring failed "
            f"for {article['title']}: {e}"
        )

        article["score"] = 0

        article["summary"] = (
            "<p>Summary unavailable.</p>"
        )

        return article

# =========================================================
# EMAIL
# =========================================================

def send_email(html):

    msg = MIMEMultipart("alternative")

    today = datetime.now().strftime(
        "%d %b %Y"
    )

    msg["Subject"] = (
        f"Daily AI Intelligence Digest "
        f"- {today}"
    )

    msg["From"] = (
        f"Daily AI News <{GMAIL}>"
    )

    msg["To"] = GMAIL

    msg.attach(
        MIMEText(html, "html")
    )

    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        server.starttls()

        server.login(
            GMAIL,
            APP_PASSWORD
        )

        server.sendmail(
            GMAIL,
            GMAIL,
            msg.as_string()
        )

# =========================================================
# BUILD HTML
# =========================================================

def build_section(title, articles):

    html = f"""
    <h2>{title}</h2>
    """

    for article in articles:

        html += f"""
        <div style="
            border:1px solid #ddd;
            border-radius:12px;
            padding:22px;
            margin-bottom:25px;
            background:#fafafa;
        ">

        <h3 style="margin-top:0;">
            {article['title']}
        </h3>

        <p>
            <strong>Source:</strong>
            {article['source']}
        </p>

        {article['summary']}

        <p>
            <a
                href="{article['link']}"
                style="
                    background:#111;
                    color:white;
                    padding:10px 14px;
                    border-radius:6px;
                    text-decoration:none;
                    display:inline-block;
                    margin-top:10px;
                "
            >
                Read More
            </a>
        </p>

        </div>
        """

    return html

def build_html(
    frontier_news,
    global_news,
    india_news
):

    html = """
    <html>

    <body style="
        font-family: Arial, sans-serif;
        max-width: 900px;
        margin: auto;
        padding: 20px;
        line-height: 1.6;
        color: #222;
    ">

    <h1>
        🧠 Daily AI Intelligence Digest
    </h1>

    <p>
    Major AI model developments,
    startup ecosystem updates,
    enterprise AI moves,
    and high-signal AI trends.
    </p>

    <hr>
    """

    html += build_section(
        "🚀 Frontier AI Labs",
        frontier_news
    )

    html += "<hr>"

    html += build_section(
        "🌍 Global AI Highlights",
        global_news
    )

    html += "<hr>"

    html += build_section(
        "🇮🇳 India AI Highlights",
        india_news
    )

    html += """
    <hr>

    <p style="
        color:gray;
        font-size:12px;
    ">
    Generated automatically using
    curated AI news sources,
    frontier AI lab updates,
    community signals,
    and Groq summarization.
    </p>

    </body>
    </html>
    """

    return html

# =========================================================
# MAIN
# =========================================================

def main():

    print("Fetching news...")

    articles = []

    # frontier AI
    articles.extend(
        fetch_rss_articles(
            FRONTIER_FEEDS,
            "global",
            "frontier"
        )
    )

    # major global AI news
    articles.extend(
        fetch_rss_articles(
            GLOBAL_RSS_FEEDS,
            "global",
            "global_news"
        )
    )

    # India AI ecosystem
    articles.extend(
        fetch_rss_articles(
            INDIA_RSS_FEEDS,
            "india",
            "india_news"
        )
    )

    # community sources
    articles.extend(fetch_reddit())
    articles.extend(fetch_github())

    articles = deduplicate_articles(
        articles
    )

    print(
        f"Collected "
        f"{len(articles)} articles"
    )

    print("Scoring articles...")

    scored_articles = []

    for article in articles:

        scored = score_article(article)

        if any(
            phrase in scored["summary"].lower()
            for phrase in BAD_SUMMARY_PHRASES
        ):
            continue

        scored_articles.append(scored)

    frontier_news = sorted(
        [
            a for a in scored_articles
            if a["category"] == "frontier"
        ],
        key=lambda x: x["score"],
        reverse=True
    )[:MAX_FRONTIER]

    global_news = sorted(
        [
            a for a in scored_articles
            if (
                a["region"] == "global"
                and
                a["category"] != "frontier"
            )
        ],
        key=lambda x: x["score"],
        reverse=True
    )[:MAX_GLOBAL]

    india_news = sorted(
        [
            a for a in scored_articles
            if a["region"] == "india"
        ],
        key=lambda x: x["score"],
        reverse=True
    )[:MAX_INDIA]

    print(
        f"Selected "
        f"{len(frontier_news)} frontier + "
        f"{len(global_news)} global + "
        f"{len(india_news)} India articles"
    )

    html = build_html(
        frontier_news,
        global_news,
        india_news
    )

    print("Sending email...")

    send_email(html)

    print("Email sent successfully")

# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":

    main()
