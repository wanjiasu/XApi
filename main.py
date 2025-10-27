"""
FastAPI service that wraps the Twitter/X media upload workflow from test.py.

Endpoints
---------
- GET /health: simple liveness probe.
- POST /tweet: upload an image and create a tweet.
- GET /twitter/callback: placeholder handler for the OAuth 1.0a callback.

Set the following environment variables before starting the server:
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET
    TWITTER_BEARER_TOKEN (optional but recommended)

Run locally with:
    uvicorn main:app --reload
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import requests
import tweepy
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class Settings(BaseModel):
    api_key: str
    api_secret: str
    access_token: str
    access_secret: str
    bearer_token: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings(
            api_key=os.environ["TWITTER_API_KEY"],
            api_secret=os.environ["TWITTER_API_SECRET"],
            access_token=os.environ["TWITTER_ACCESS_TOKEN"],
            access_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        )
    except KeyError as exc:
        missing = exc.args[0]
        raise RuntimeError(f"Missing required environment variable: {missing}") from exc


class TweetRequest(BaseModel):
    text: str
    image_path: str = "image.png"


app = FastAPI(title="OurMixPost Twitter Service")


def upload_media_v1(settings: Settings, image_path: Path) -> Optional[str]:
    """Upload media using the legacy upload endpoint with OAuth1 signing."""
    logger.info("Trying media upload via v1.1 OAuth endpoint")
    auth = OAuth1(
        settings.api_key,
        settings.api_secret,
        settings.access_token,
        settings.access_secret,
    )
    
    try:
        files = {"media": (image_path.name, image_path.read_bytes(), "image/png")}
        data = {"media_category": "tweet_image", "media_type": "image/png"}
        
        response = requests.post(
            "https://upload.twitter.com/1.1/media/upload.json", 
            auth=auth, 
            files=files, 
            data=data, 
            timeout=60,  # 增加超时时间
            verify=True  # 确保SSL验证
        )
        
        logger.info("v1.1 upload response: status=%d, content_length=%d", 
                   response.status_code, len(response.content))
        
        if response.status_code == 200:
            result = response.json()
            media_id = result.get("media_id_string")
            logger.info("v1.1 upload successful, media_id: %s", media_id)
            return media_id
        else:
            logger.error("Media upload v1 failed: %s - %s", response.status_code, response.text)
            # 记录响应头信息用于调试
            logger.error("Response headers: %s", dict(response.headers))
            return None
            
    except requests.exceptions.Timeout:
        logger.error("v1.1 upload timeout after 60 seconds")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error("v1.1 upload connection error: %s", str(e))
        return None
    except requests.exceptions.RequestException as e:
        logger.error("v1.1 upload request error: %s", str(e))
        return None
    except Exception as e:
        logger.error("v1.1 upload unexpected error: %s", str(e))
        return None


def upload_media_bearer(settings: Settings, image_path: Path) -> Optional[str]:
    """Upload media using bearer token if available."""
    if not settings.bearer_token:
        logger.info("Bearer token not available, skipping bearer upload")
        return None
        
    logger.info("Trying media upload via bearer token")
    headers = {"Authorization": f"Bearer {settings.bearer_token}"}
    
    try:
        files = {"media": (image_path.name, image_path.read_bytes(), "image/png")}
        data = {"media_category": "tweet_image", "media_type": "image/png"}
        
        response = requests.post(
            "https://upload.twitter.com/1.1/media/upload.json", 
            headers=headers, 
            files=files, 
            data=data, 
            timeout=60,  # 增加超时时间
            verify=True  # 确保SSL验证
        )
        
        logger.info("Bearer upload response: status=%d, content_length=%d", 
                   response.status_code, len(response.content))
        
        if response.status_code == 200:
            result = response.json()
            media_id = result.get("media_id_string")
            logger.info("Bearer upload successful, media_id: %s", media_id)
            return media_id
        else:
            logger.error("Bearer upload failed: %s - %s", response.status_code, response.text)
            logger.error("Response headers: %s", dict(response.headers))
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Bearer upload timeout after 60 seconds")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error("Bearer upload connection error: %s", str(e))
        return None
    except requests.exceptions.RequestException as e:
        logger.error("Bearer upload request error: %s", str(e))
        return None
    except Exception as e:
        logger.error("Bearer upload unexpected error: %s", str(e))
        return None


def upload_media_tweepy(settings: Settings, image_path: Path) -> Optional[str]:
    """Fallback to tweepy API for media upload."""
    logger.info("Trying media upload via Tweepy API")
    
    try:
        auth = tweepy.OAuth1UserHandler(
            settings.api_key,
            settings.api_secret,
            settings.access_token,
            settings.access_secret,
        )
        api = tweepy.API(auth, wait_on_rate_limit=True)  # 添加速率限制等待
        
        logger.info("Uploading file: %s (size: %d bytes)", image_path, image_path.stat().st_size)
        media = api.media_upload(filename=str(image_path))
        
        logger.info("Tweepy upload successful, media_id: %s", media.media_id_string)
        return media.media_id_string
        
    except tweepy.TooManyRequests:
        logger.error("Tweepy upload failed: Rate limit exceeded")
        return None
    except tweepy.Unauthorized:
        logger.error("Tweepy upload failed: Unauthorized - check API credentials")
        return None
    except tweepy.Forbidden:
        logger.error("Tweepy upload failed: Forbidden - check API permissions")
        return None
    except tweepy.NotFound:
        logger.error("Tweepy upload failed: API endpoint not found")
        return None
    except tweepy.TwitterServerError:
        logger.error("Tweepy upload failed: Twitter server error")
        return None
    except Exception as exc:  # Tweepy raises varied exceptions
        logger.error("Tweepy upload failed with exception: %s (type: %s)", str(exc), type(exc).__name__)
        return None


UPLOADERS: tuple[Callable[[Settings, Path], Optional[str]], ...] = (
    upload_media_v1,
    upload_media_bearer,
    upload_media_tweepy,
)


def upload_media(settings: Settings, image_path: Path) -> Optional[str]:
    """Try each uploader in sequence until one succeeds."""
    if not image_path.exists():
        logger.error("Image file not found: %s", image_path)
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # 记录文件信息
    file_size = image_path.stat().st_size
    logger.info("Starting media upload for file: %s (size: %d bytes)", image_path, file_size)
    
    # 检查文件大小限制 (Twitter限制为5MB)
    if file_size > 5 * 1024 * 1024:
        logger.error("File too large: %d bytes (max 5MB)", file_size)
        return None
    
    for i, uploader in enumerate(UPLOADERS, 1):
        logger.info("Attempting upload method %d/%d: %s", i, len(UPLOADERS), uploader.__name__)
        try:
            media_id = uploader(settings, image_path)
            if media_id:
                logger.info("Media upload succeeded via %s, media_id: %s", uploader.__name__, media_id)
                return media_id
            else:
                logger.warning("Upload method %s returned None", uploader.__name__)
        except Exception as e:
            logger.error("Upload method %s raised exception: %s", uploader.__name__, str(e))
    
    logger.error("All %d upload methods failed", len(UPLOADERS))
    return None


def create_twitter_client(settings: Settings) -> tweepy.Client:
    return tweepy.Client(
        consumer_key=settings.api_key,
        consumer_secret=settings.api_secret,
        access_token=settings.access_token,
        access_token_secret=settings.access_secret,
        bearer_token=settings.bearer_token,
        wait_on_rate_limit=True,
    )


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.post("/tweet")
async def tweet(payload: TweetRequest):
    logger.info("Received tweet request: text='%s', image_path='%s'", payload.text, payload.image_path)
    
    try:
        settings = get_settings()
        logger.info("Settings loaded successfully")
    except Exception as e:
        logger.error("Failed to load settings: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}") from e
    
    image_path = Path(payload.image_path)
    logger.info("Processing image path: %s (absolute: %s)", image_path, image_path.absolute())
    
    try:
        media_id = upload_media(settings, image_path)
    except FileNotFoundError as exc:
        logger.error("File not found error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected error during media upload: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Media upload error: {str(exc)}") from exc

    if not media_id:
        logger.error("All media upload attempts failed for file: %s", image_path)
        raise HTTPException(status_code=502, detail="All media upload attempts failed")

    logger.info("Media uploaded successfully, creating tweet with media_id: %s", media_id)
    
    try:
        client = create_twitter_client(settings)
        response = client.create_tweet(text=payload.text, media_ids=[media_id])
        tweet_id = response.data.get("id")
        logger.info("Tweet created successfully: tweet_id=%s", tweet_id)
        return {"tweet_id": tweet_id, "media_id": media_id}
    except Exception as exc:
        logger.error("Failed to create tweet: %s", str(exc))
        raise HTTPException(status_code=502, detail=f"Tweet creation failed: {str(exc)}") from exc


@app.get("/twitter/callback")
async def twitter_callback(
    oauth_token: Optional[str] = Query(default=None),
    oauth_verifier: Optional[str] = Query(default=None),
    denied: Optional[str] = Query(default=None),
):
    """
    Minimal placeholder handler for the OAuth callback URL configured in the Twitter App.
    Persist oauth_token/oauth_verifier in a secure store if you need to mint long-lived tokens.
    """
    if denied:
        logger.warning("User denied authorization for token %s", denied)
        return {"status": "denied", "token": denied}
    if not oauth_token or not oauth_verifier:
        raise HTTPException(status_code=400, detail="Missing oauth_token or oauth_verifier")

    logger.info("Received oauth callback token=%s verifier=%s", oauth_token, oauth_verifier)
    # Exchange oauth_token + oauth_verifier for access tokens here if needed.
    return {"status": "received", "oauth_token": oauth_token}
