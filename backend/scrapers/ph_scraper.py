import requests
from backend.config import settings

def run():
    if not settings.PRODUCTHUNT_TOKEN:
        print("Product Hunt scraper: Missing token, skipping.")
        return []

    # Product Hunt V2 GraphQL API
    url = "https://api.producthunt.com/v2/api/graphql"
    headers = {"Authorization": f"Bearer {settings.PRODUCTHUNT_TOKEN}"}
    
    # Query for newest posts or specific categories
    query = """
    {
      posts(first: 50, order: NEWEST) {
        edges {
          node {
            id
            name
            tagline
            description
            votesCount
            website
          }
        }
      }
    }
    """
    
    posts = []
    try:
        r = requests.post(url, json={'query': query}, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                content = f"{node.get('name')}: {node.get('tagline')}\n{node.get('description') or ''}"
                posts.append({
                    "id": f"ph_{node.get('id')}",
                    "source": "producthunt",
                    "content": content,
                    "metadata": {
                        "votes": node.get("votesCount", 0),
                        "url": node.get("website")
                    }
                })
        else:
            print(f"Product Hunt API error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Product Hunt scraper error: {e}")

    print(f"Product Hunt: collected {len(posts)} posts")
    return posts
