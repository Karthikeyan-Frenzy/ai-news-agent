import os
import feedparser
import requests
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ======================
# CONFIG
# ======================

GMAIL = os.environ["GMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

RSS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://openai.com/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
]

# ======================
# FETCH NEWS
# ======================

def fetch_news():

    articles = []

    for url in RSS_FEEDS:

        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", "")
            })

    return articles[:5]

# ======================
# SUMMARIZE WITH GROQ
# ======================

def summarize(article):

    prompt = f"""
    Summarize this AI/ML news article.

    Give:
    - 3 concise bullet points
    - Why this matters

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
            "temperature": 0.3
        }
    )

    result = response.json()

    return result["choices"][0]["message"]["content"]

# ======================
# SEND EMAIL
# ======================

def send_email(content):

    msg = MIMEMultipart("alternative")

    msg["Subject"] = "Daily AI News Digest"
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
# MAIN
# ======================

def main():

    news = fetch_news()

    html = """
    <h2>Daily AI/ML News Digest</h2>
    """

    for article in news:

        try:

            summary = summarize(article)

        except Exception as e:

            summary = f"Failed to summarize article: {str(e)}"

        html += f"""
        <hr>

        <h3>{article['title']}</h3>

        <p>{summary}</p>

        <p>
            <a href="{article['link']}">
                Read Full Article
            </a>
        </p>
        """

    send_email(html)

if __name__ == "__main__":
    main()