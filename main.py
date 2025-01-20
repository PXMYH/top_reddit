from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel
import httpx
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reddit Data Parser")

# Create templates directory if it doesn't exist
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

# Save the HTML template
html_path = templates_dir / "index.html"

@app.get("/", response_class=HTMLResponse)
async def root():
    return html_path.read_text()

# Models
class RedditPost(BaseModel):
    title: str
    ups: int
    upvote_ratio: float

class RedditResponse(BaseModel):
    subreddit: str
    timeframe: str
    posts: List[RedditPost]

async def fetch_reddit_data(subreddit: str, timeframe: str) -> dict:
    """
    Fetch data from Reddit API
    """
    base_url = f"https://old.reddit.com/r/{subreddit}/top.json"
    params = {
        "t": timeframe,
        "utm_source": "reddit",
        "utm_medium": "usertext",
        "utm_name": "redditdev"
    }
    
    headers = {
        "User-Agent": "FastAPI Reddit Parser v1.0"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise HTTPException(status_code=503, detail=f"Error fetching data from Reddit: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def parse_reddit_data(data: dict) -> List[RedditPost]:
    """
    Parse Reddit API response and extract required fields
    """
    posts = []
    try:
        for post in data["data"]["children"]:
            post_data = post["data"]
            posts.append(
                RedditPost(
                    title=post_data["title"],
                    ups=post_data["ups"],
                    upvote_ratio=post_data["upvote_ratio"]
                )
            )
        return posts
    except KeyError as e:
        logger.error(f"Error parsing Reddit data: {e}")
        raise HTTPException(status_code=500, detail="Error parsing Reddit response")

@app.get("/reddit/{subreddit}", response_model=RedditResponse)
async def get_reddit_data(subreddit: str, timeframe: str = "year"):
    """
    Get Reddit data for a specific subreddit and timeframe
    
    Parameters:
    - subreddit: Name of the subreddit
    - timeframe: Time range (hour, day, week, month, year, all)
    
    Returns:
    - RedditResponse object containing parsed post data
    """
    # Validate timeframe
    valid_timeframes = {"hour", "day", "week", "month", "year", "all"}
    if timeframe not in valid_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
        )
    
    # Fetch data from Reddit
    data = await fetch_reddit_data(subreddit, timeframe)
    
    # Parse the response
    posts = parse_reddit_data(data)
    
    return RedditResponse(
        subreddit=subreddit,
        timeframe=timeframe,
        posts=posts
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)