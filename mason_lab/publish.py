"""Uploaders for finished vertical clips. Both use the platforms' official APIs."""
from __future__ import annotations

import json
import os
from typing import Any

from .config import env


def youtube_upload(http: Any, path: str, title: str, description: str, tags: list[str],
                   privacy: str = "public") -> str:
    """Upload a Short via YouTube Data API v3 (resumable upload). Returns the video URL.

    Needs YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (see README). Each upload costs 1,600 of
    your 10,000 daily quota units, so ~6 uploads/day on a default project.
    """
    tok = http.post("https://oauth2.googleapis.com/token", data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=20)
    tok.raise_for_status()
    auth = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15],
                        "categoryId": "20"},  # 20 = Gaming
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    init = http.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                     headers={**auth, "Content-Type": "application/json; charset=UTF-8",
                              "X-Upload-Content-Type": "video/mp4"},
                     data=json.dumps(meta), timeout=30)
    init.raise_for_status()
    with open(path, "rb") as f:
        up = http.put(init.headers["Location"], headers={**auth, "Content-Type": "video/mp4"}, data=f, timeout=600)
    up.raise_for_status()
    return f"https://youtube.com/shorts/{up.json()['id']}"


def tiktok_upload_draft(http: Any, path: str) -> str:
    """Send the clip to your TikTok inbox as a draft (Content Posting API, video.upload scope).

    You open TikTok, add the caption/sound and post. Drafts work without TikTok's app audit;
    direct public posting needs an audited app, and a human final check is safer anyway.
    """
    token = env("TIKTOK_ACCESS_TOKEN")
    size = os.path.getsize(path)
    chunk = min(size, 10_000_000)
    n_chunks = max(1, size // chunk)  # TikTok: last chunk absorbs the remainder
    init = http.post("https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                     json={"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                           "chunk_size": chunk, "total_chunk_count": n_chunks}}, timeout=30)
    init.raise_for_status()
    data = init.json()["data"]
    with open(path, "rb") as f:
        for i in range(n_chunks):
            start = i * chunk
            end = size - 1 if i == n_chunks - 1 else start + chunk - 1
            f.seek(start)
            body = f.read(end - start + 1)
            r = http.put(data["upload_url"], data=body, timeout=600, headers={
                "Content-Type": "video/mp4", "Content-Range": f"bytes {start}-{end}/{size}"})
            r.raise_for_status()
    return data.get("publish_id", "")


__all__ = ["youtube_upload", "tiktok_upload_draft"]
