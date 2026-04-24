from google_play_scraper import reviews, Sort

# Apps to mine — competitors in your target niche
TARGET_APPS = [
    "com.notion.id",
    "com.todoist.app",
    "com.asana.app",
    "com.basecamp.bc3android",
]

def run():
    posts = []
    for app_id in TARGET_APPS:
        try:
            result, _ = reviews(
                app_id,
                lang='en', country='us',
                sort=Sort.NEWEST,
                count=200,
                filter_score_with=None
            )
            for r in result:
                # Only 1-3 star reviews — these contain the pain points
                if r['score'] > 2:
                    continue

                posts.append({
                    "id": f"ps_{r['reviewId']}",
                    "source": "playstore",
                    "content": r['content'],
                    "metadata": {
                        "app_id": app_id,
                        "rating": r['score'],
                        "thumbs_up": r.get('thumbsUpCount', 0)
                    }
                })
        except Exception as e:
            print(f"Play Store scraper error for {app_id}: {e}")

    print(f"Play Store: collected {len(posts)} reviews")
    return posts
