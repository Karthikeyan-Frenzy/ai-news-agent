import os
import requests
import smtplib
import feedparser
import json

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ======================
# CONFIG
# ======================

GMAIL = os.environ["GMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

MAX_GLOBAL = 3
MAX_INDIA = 2

# ======================
# INDIA RSS SOURCES
# ======================

INDIA_RSS_FEEDS = [
    "https://analyticsindiamag.com/feed/",
    "https://entrackr.com/feed/",
    "https://inc42.com/feed/",
    "https://yourstory.com/feed"
]

# ======================
# AI KEYWORDS
# ======================

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
    "rag",
    "agent",
    "agents",
    "copilot",
    "vector database",
    "inference",
    "fine tuning",
    "automation",
    "genai",
    "startup"
]

BLOCKED_KEYWORDS = [
    "daily roundup",
    "weekly roundup",
    "morning briefing",
    "podcast",
    "event",
    "webinar",
    "top stories",
    "live updates"
]

# ======================
# HELPERS
# ======================

def contains_ai_keywords(text):

    text = text.lower()

    return any(
        keyword in text
        for keyword in AI_KEYWORDS
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

# ======================
# HACKER NEWS
# ======================

def fetch_hackernews():

    articles = []

    try:

        top_ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=20
        ).json()[:40]

        for story_id in top_ids:

            item = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=20
            ).json()

            if not item:
                continue

            title = item.get("title", "")

            if not contains_ai_keywords(title):
                continue

            if is_low_quality(title):
                continue

            articles.append({
                "title": title,
                "summary": item.get("text", ""),
                "link": item.get(
                    "url",
                    "https://news.ycombinator.com"
                ),
                "source": "Hacker News",
                "region": "global"
            })

    except Exception as e:

        print(f"HackerNews error: {e}")

    return articles

# ======================
# REDDIT
# ======================

def fetch_reddit():

    articles = []

    subreddits = [
        "MachineLearning",
        "LocalLLaMA",
        "artificial",
        "singularity"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        for subreddit in subreddits:

            url = (
                f"https://www.reddit.com/r/"
                f"{subreddit}/hot.json?limit=10"
            )

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            posts = response.json()["data"]["children"]

            for post in posts:

                data = post["data"]

                title = data.get("title", "")

                if not contains_ai_keywords(title):
                    continue

                if is_low_quality(title):
                    continue

                articles.append({
                    "title": title,
                    "summary": data.get(
                        "selftext",
                        ""
                    )[:1000],
                    "link": (
                        "https://reddit.com" +
                        data.get("permalink", "")
                    ),
                    "source": f"Reddit - r/{subreddit}",
                    "region": "global"
                })

    except Exception as e:

        print(f"Reddit error: {e}")

    return articles

# ======================
# GITHUB
# ======================

def fetch_github():

    articles = []

    try:

        url = (
            "https://api.github.com/"
            "search/repositories"
        )

        params = {
            "q": (
                "llm OR rag OR agents OR "
                "openai OR anthropic OR "
                "inference OR vector-db"
            ),
            "sort": "stars",
            "order": "desc",
            "per_page": 10
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        repos = response.json().get("items", [])

        for repo in repos:

            title = repo.get("full_name", "")

            desc = repo.get("description", "")

            if is_low_quality(title):
                continue

            articles.append({
                "title": f"Trending GitHub Repo: {title}",
                "summary": desc,
                "link": repo.get("html_url", ""),
                "source": f"GitHub - {title}",
                "region": "global"
            })

    except Exception as e:

        print(f"GitHub error: {e}")

    return articles

# ======================
# INDIA RSS
# ======================

def fetch_india_news():

    articles = []

    try:

        for url in INDIA_RSS_FEEDS:

            feed = feedparser.parse(url)

            for entry in feed.entries[:10]:

                title = entry.get("title", "")

                summary = entry.get("summary", "")

                combined = f"{title} {summary}"

                if not contains_ai_keywords(combined):
                    continue

                if is_low_quality(combined):
                    continue

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": feed.feed.get(
                        "title",
                        "India RSS"
                    ),
                    "region": "india"
                })

    except Exception as e:

        print(f"India RSS error: {e}")

    return articles

# ======================
# GROQ SCORING + SUMMARY
# ======================

def score_article(article):

    prompt = f"""
You are an elite AI news editor.

Evaluate this article.

Return ONLY valid JSON.

Format:

{{
    "importance": 1-10,
    "ai_relevance": 1-10,
    "india_relevance": 1-10,
    "score": total score out of 30,
    "summary": "HTML formatted summary"
}}

Rules for summary:
- Use proper HTML
- DO NOT use markdown
- Use <ul>, <li>, <b>, <p>
- Keep concise
- No generic filler
- Mention why this matters

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

        # Remove markdown code blocks if present
        content = content.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        parsed = json.loads(content)

        article["score"] = parsed.get(
            "score",
            0
        )

        article["summary"] = parsed.get(
            "summary",
            "<p>No summary available</p>"
        )

        return article

    except Exception as e:

        print(
            f"Scoring failed for "
            f"{article['title']}: {e}"
        )

        article["score"] = 0

        article["summary"] = (
            "<p>Summary unavailable.</p>"
        )

        return article

# ======================
# EMAIL
# ======================

def send_email(html):

    msg = MIMEMultipart("alternative")

    today = datetime.now().strftime("%d %b %Y")

    msg["Subject"] = (
        f"Daily AI Intelligence Digest - {today}"
    )

    msg["From"] = GMAIL
    msg["To"] = GMAIL

    msg.attach(MIMEText(html, "html"))

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

# ======================
# BUILD HTML
# ======================

def build_html(global_news, india_news):

    html = """
    <html>

    <body style="
        font-family: Arial, sans-serif;
        max-width: 900px;
        margin: auto;
        line-height: 1.6;
        color: #222;
        padding: 20px;
    ">

    <h1>🧠 Daily AI Intelligence Digest</h1>

    <p>
    Curated AI updates from Hacker News,
    Reddit, GitHub, and Indian startup ecosystem.
    </p>

    <hr>

    <h2>🌍 Global AI Highlights</h2>
    """

    for article in global_news:

        html += f"""
        <div style="
            border:1px solid #ddd;
            border-radius:10px;
            padding:20px;
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

    html += """
    <hr>

    <h2>🇮🇳 India AI Highlights</h2>
    """

    for article in india_news:

        html += f"""
        <div style="
            border:1px solid #ddd;
            border-radius:10px;
            padding:20px;
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

    html += """
    <hr>

    <p style="
        color:gray;
        font-size:12px;
    ">
    Generated automatically using
    multi-source AI aggregation
    and Groq summarization.
    </p>

    </body>
    </html>
    """

    return html

# ======================
# MAIN
# ======================

def main():

    print("Collecting news...")

    articles = []

    articles.extend(fetch_hackernews())
    articles.extend(fetch_reddit())
    articles.extend(fetch_github())
    articles.extend(fetch_india_news())

    articles = deduplicate_articles(
        articles
    )

    print(
        f"Collected "
        f"{len(articles)} raw articles"
    )

    print("Scoring articles...")

    scored_articles = []

    for article in articles:

        scored = score_article(article)

        # Skip bad summaries
        bad_phrases = [
            "does not contain",
            "likely includes",
            "may include",
            "unfortunately"
        ]

        if any(
            phrase in scored["summary"].lower()
            for phrase in bad_phrases
        ):
            continue

        scored_articles.append(scored)

    global_news = sorted(
        [
            a for a in scored_articles
            if a["region"] == "global"
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
        f"{len(global_news)} global + "
        f"{len(india_news)} India articles"
    )

    html = build_html(
        global_news,
        india_news
    )

    print("Sending email...")

    send_email(html)

    print("Email sent successfully")

# ======================
# ENTRY
# ======================

if __name__ == "__main__":

    main()
