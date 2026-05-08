import os
import feedparser
import requests
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ======================
# CONFIG
# ======================

GMAIL = os.environ["GMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

RSS_FEEDS = [
    # India-focused AI / startup / tech
    "https://analyticsindiamag.com/feed/",
    "https://inc42.com/feed/",
    "https://entrackr.com/feed/",
    "https://yourstory.com/feed/",
    "https://www.moneycontrol.com/rss/technology.xml",

    # Global AI / tech
    "https://hnrss.org/frontpage",
    "https://openai.com/news/rss.xml",
]

AI_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "llm",
    "gpt",
    "genai",
    "openai",
    "anthropic",
    "gemini",
    "deepseek",
    "mistral",
    "claude",
    "nvidia",
    "agentic",
    "rag",
    "copilot",
    "automation"
]

MAX_ARTICLES = 8

# ======================
# HELPERS
# ======================

def is_ai_related(text):

    text = text.lower()

    return any(keyword in text for keyword in AI_KEYWORDS)

def is_recent(entry):

    try:

        if hasattr(entry, "published_parsed") and entry.published_parsed:

            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)

            return (now - published) <= timedelta(hours=24)

    except Exception:
        pass

    # If no publish time exists, allow article
    return True

def clean_html(raw_html):

    import re

    clean = re.compile("<.*?>")

    return re.sub(clean, "", raw_html)

# ======================
# FETCH NEWS
# ======================

def fetch_news():

    articles = []

    seen_titles = set()

    for url in RSS_FEEDS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries[:15]:

                title = entry.get("title", "")
                summary = clean_html(entry.get("summary", ""))

                combined_text = f"{title} {summary}"

                if not is_ai_related(combined_text):
                    continue

                if not is_recent(entry):
                    continue

                normalized_title = title.lower().strip()

                if normalized_title in seen_titles:
                    continue

                seen_titles.add(normalized_title)

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": feed.feed.get("title", "Unknown Source")
                })

        except Exception as e:

            print(f"Failed to parse feed {url}: {e}")

    return articles[:MAX_ARTICLES]

# ======================
# SUMMARIZE WITH GROQ
# ======================

def summarize(article):

    prompt = f"""
You are an AI news analyst.

Summarize this article in:

1. Three concise bullet points
2. Why this matters to AI/Data professionals

Keep the tone crisp, informative, and practical.

TITLE:
{article['title']}

CONTENT:
{article['summary']}
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
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

    return result["choices"][0]["message"]["content"]

# ======================
# SEND EMAIL
# ======================

def send_email(content):

    msg = MIMEMultipart("alternative")

    today = datetime.now().strftime("%d %b %Y")

    msg["Subject"] = f"Daily AI/ML News Digest - {today}"
    msg["From"] = GMAIL
    msg["To"] = GMAIL

    msg.attach(MIMEText(content, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:

        server.starttls()

        server.login(GMAIL, APP_PASSWORD)

        server.sendmail(
            GMAIL,
            GMAIL,
            msg.as_string()
        )

# ======================
# BUILD HTML
# ======================

def build_html(news):

    html = """
    <html>
    <body style="
        font-family: Arial, sans-serif;
        max-width: 800px;
        margin: auto;
        line-height: 1.6;
        color: #222;
    ">

    <h1>🧠 Daily AI/ML News Digest</h1>

    <p>
        Curated AI, ML, startup, and enterprise tech updates.
    </p>
    """

    for article in news:

        try:

            summary = summarize(article)

        except Exception as e:

            summary = f"Failed to summarize article:<br>{str(e)}"

        formatted_summary = summary.replace("\n", "<br>")

        html += f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
        ">

            <h2 style="margin-top: 0;">
                {article['title']}
            </h2>

            <p>
                <strong>Source:</strong> {article['source']}
            </p>

            <p>
                {formatted_summary}
            </p>

            <p>
                <a
                    href="{article['link']}"
                    style="
                        background-color: #111;
                        color: white;
                        padding: 10px 14px;
                        text-decoration: none;
                        border-radius: 6px;
                    "
                >
                    Read Full Article
                </a>
            </p>

        </div>
        """

    html += """
    <hr>

    <p style="font-size: 12px; color: gray;">
        Generated automatically using RSS feeds + Groq LLM summarization.
    </p>

    </body>
    </html>
    """

    return html

# ======================
# MAIN
# ======================

def main():

    print("Fetching latest AI news...")

    news = fetch_news()

    if not news:

        print("No relevant news articles found.")

        return

    print(f"Found {len(news)} relevant articles.")

    html = build_html(news)

    print("Sending email...")

    send_email(html)

    print("Email sent successfully.")

# ======================
# ENTRY
# ======================

if __name__ == "__main__":

    main()
