import os
import feedparser
import smtplib
import google.generativeai as genai

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ======================
# CONFIG
# ======================

GMAIL = os.environ["GMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

RSS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://openai.com/news/rss.xml"
]

# ======================
# GEMINI SETUP
# ======================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash")

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
# SUMMARIZE
# ======================

def summarize(article):

    prompt = f"""
    Summarize this AI news in 3 concise bullet points.

    TITLE:
    {article['title']}

    CONTENT:
    {article['summary']}
    """

    response = model.generate_content(prompt)

    return response.text

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

    html = "<h2>Daily AI News Digest</h2>"

    for article in news:

        summary = summarize(article)

        html += f"""
        <hr>
        <h3>{article['title']}</h3>
        <p>{summary}</p>
        <a href="{article['link']}">Read Full Article</a>
        """

    send_email(html)

if __name__ == "__main__":
    main()
