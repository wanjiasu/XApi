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
    files = {"media": (image_path.name, image_path.read_bytes(), "image/png")}
    data = {"media_category": "tweet_image", "media_type": "image/png"}
    response = requests.post(
        "https://upload.twitter.com/1.1/media/upload.json", auth=auth, files=files, data=data, timeout=30
    )
    if response.status_code == 200:
        return response.json().get("media_id_string")
    logger.warning("Media upload v1 failed: %s - %s", response.status_code, response.text)
    return None


def upload_media_bearer(settings: Settings, image_path: Path) -> Optional[str]:
    """Upload media using bearer token if available."""
    if not settings.bearer_token:
        return None
    logger.info("Trying media upload via bearer token")
    headers = {"Authorization": f"Bearer {settings.bearer_token}"}
    files = {"media": (image_path.name, image_path.read_bytes(), "image/png")}
    data = {"media_category": "tweet_image", "media_type": "image/png"}
    response = requests.post(
        "https://upload.twitter.com/1.1/media/upload.json", headers=headers, files=files, data=data, timeout=30
    )
    if response.status_code == 200:
        return response.json().get("media_id_string")
    logger.warning("Bearer upload failed: %s - %s", response.status_code, response.text)
    return None


def upload_media_tweepy(settings: Settings, image_path: Path) -> Optional[str]:
    """Fallback to tweepy API for media upload."""
    logger.info("Trying media upload via Tweepy API")
    auth = tweepy.OAuth1UserHandler(
        settings.api_key,
        settings.api_secret,
        settings.access_token,
        settings.access_secret,
    )
    api = tweepy.API(auth)
    try:
        media = api.media_upload(filename=str(image_path))
        return media.media_id_string
    except Exception as exc:  # Tweepy raises varied exceptions
        logger.warning("Tweepy upload failed: %s", exc)
        return None


UPLOADERS: tuple[Callable[[Settings, Path], Optional[str]], ...] = (
    upload_media_v1,
    upload_media_bearer,
    upload_media_tweepy,
)


def upload_media(settings: Settings, image_path: Path) -> Optional[str]:
    """Try each uploader in sequence until one succeeds."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    for uploader in UPLOADERS:
        media_id = uploader(settings, image_path)
        if media_id:
            logger.info("Media upload succeeded via %s", uploader.__name__)
            return media_id
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
    settings = get_settings()
    image_path = Path(payload.image_path)
    try:
        media_id = upload_media(settings, image_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not media_id:
        raise HTTPException(status_code=502, detail="All media upload attempts failed")

    client = create_twitter_client(settings)
    response = client.create_tweet(text=payload.text, media_ids=[media_id])
    tweet_id = response.data.get("id")
    return {"tweet_id": tweet_id, "media_id": media_id}


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
