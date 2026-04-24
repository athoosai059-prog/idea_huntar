import praw
import hashlib
from backend.config import settings

SUBREDDITS = ["SideProject", "startups", "webdev", "entrepreneur", "freelance"]
COMPLAINT_KEYWORDS = [
    "wish there was", "why isn't there", "I need an app",
    "frustrated with", "nobody has built", "can't find a tool",
    "hate that", "annoying that", "if only there was"
]

def run():
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        print("Reddit scraper: Missing credentials, skipping.")
        return []

    reddit = praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
    )

    posts = []
    for sub_name in SUBREDDITS:
        try:
            sub = reddit.subreddit(sub_name)
            for submission in sub.top(time_filter="month", limit=300):
                # Score filter — skip low-engagement posts
                if submission.score < 10:
                    continue

                content = f"{submission.title}\n{submission.selftext[:2000]}"

                # Keyword filter — prioritize complaint/wish posts
                has_signal = any(kw.lower() in content.lower() for kw in COMPLAINT_KEYWORDS)

                post_id = hashlib.md5(submission.id.encode()).hexdigest()
                posts.append({
                    "id": f"reddit_{post_id}",
                    "source": "reddit",
                    "content": content,
                    "metadata": {
                        "subreddit": sub_name,
                        "upvotes": submission.score,
                        "url": f"https://reddit.com{submission.permalink}",
                        "has_signal": has_signal
                    }
                })
        except Exception as e:
            print(f"Reddit scraper error for {sub_name}: {e}")

    print(f"Reddit: collected {len(posts)} posts")
    return posts
