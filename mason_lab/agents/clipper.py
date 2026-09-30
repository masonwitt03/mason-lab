from __future__ import annotations

import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import env
from ..models import HIGH, LOW, NORMAL, Alert
from ..publish import tiktok_upload_draft, youtube_upload
from .base import Agent, AgentContext

HELIX = "https://api.twitch.tv/helix"
KICK = "https://api.kick.com/public/v1"

# Blurred full-frame background + the original 16:9 video centered: the standard Shorts/TikTok look.
VERTICAL_FILTER = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                   "[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")


def pick_clips(clips: list[dict], already: set[str], min_views: int, max_n: int,
               min_s: float = 8, max_s: float = 60) -> list[dict]:
    """Highest-viewed clips that fit Shorts/TikTok length and haven't been posted yet."""
    ok = [c for c in clips if c["id"] not in already and c.get("view_count", 0) >= min_views
          and min_s <= c.get("duration", 0) <= max_s]
    return sorted(ok, key=lambda c: c["view_count"], reverse=True)[:max_n]


def caption_for(clip: dict, streamer: dict) -> tuple[str, str, list[str]]:
    name = clip.get("broadcaster_name") or streamer["login"]
    tags = streamer.get("hashtags") or [name.lower(), "twitch", "gaming", "clips", "shorts"]
    title = f"{clip['title'].strip()[:80]} | {name}"
    desc = (f"{clip['title']}\n\nFull credit: {name} - https://twitch.tv/{streamer['login']}\n"
            f"Original clip: {clip['url']}\n\n" + " ".join(f"#{t}" for t in tags))
    return title, desc, tags


class ClipperAgent(Agent):
    """Pulls the day's most-viewed clips from streamers you're approved to clip, turns them into
    9:16 Shorts/TikToks with credit, and uploads (YouTube) or drafts them (TikTok).

    Also scouts which streamers are blowing up on Twitch/Kick so you know who to approach
    about clipping (many run paid clipping programs).
    """

    name = "clipper"
    default_interval_min = 180
    default_cooldown_h = 24 * 30

    def run(self, ctx: AgentContext) -> list[Alert]:
        alerts: list[Alert] = []
        token = self._twitch_token(ctx)
        if token:
            hdr = {"Client-Id": env("TWITCH_CLIENT_ID"), "Authorization": f"Bearer {token}"}
            alerts += self._scout_twitch(ctx, hdr)
            alerts += self._process_twitch(ctx, hdr)
        alerts += self._scout_kick(ctx)
        return alerts

    # --- discovery -------------------------------------------------------------------------
    def _twitch_token(self, ctx: AgentContext) -> str | None:
        cid, secret = env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET")
        if not (cid and secret):
            return None
        cached = ctx.store.get(self.name, "twitch_token")
        if cached and cached["exp"] > time.time() + 300:
            return cached["token"]
        r = ctx.http.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}, timeout=20)
        r.raise_for_status()
        j = r.json()
        ctx.store.put(self.name, "twitch_token", {"token": j["access_token"], "exp": time.time() + j["expires_in"]})
        return j["access_token"]

    def _scout_twitch(self, ctx: AgentContext, hdr: dict) -> list[Alert]:
        streams = self.get_json(ctx.http, f"{HELIX}/streams", headers=hdr,
                                params={"first": 50, "language": self.cfg.get("language", "en")}).get("data", [])
        approved = {s["login"].lower() for s in (self.cfg.get("streamers") or [])}
        top = [s for s in streams if s["user_login"].lower() not in approved][:10]
        if not top:
            return []
        body = "\n".join(f"- {s['user_name']} ({s['game_name']}) {s['viewer_count']:,} viewers" for s in top)
        body += ("\n\nHigh viewers = clips that travel. Check if they run a clipping program "
                 "(e.g. a Discord 'clipper' channel or a paid clip campaign) and add them once approved.")
        return [Alert(agent=self.name, key=f"scout:twitch:{time.strftime('%Y-%m-%d')}",
                      title="Top Twitch streamers live now", body=body, priority=LOW,
                      data={"top": [s["user_login"] for s in top]})]

    def _scout_kick(self, ctx: AgentContext) -> list[Alert]:
        cid, secret = env("KICK_CLIENT_ID"), env("KICK_CLIENT_SECRET")
        if not (cid and secret):
            return []
        r = ctx.http.post("https://id.kick.com/oauth/token", data={
            "client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}, timeout=20)
        r.raise_for_status()
        hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
        live = self.get_json(ctx.http, f"{KICK}/livestreams", headers=hdr,
                             params={"sort": "viewer_count", "limit": 10}).get("data", [])
        if not live:
            return []
        body = "\n".join(f"- {s.get('slug') or s.get('broadcaster_user_id')}: {s.get('viewer_count', 0):,} viewers"
                         f" ({(s.get('category') or {}).get('name', '')})" for s in live)
        body += "\n\nKick has no public clips API yet, so Kick clips have to be grabbed manually for now."
        return [Alert(agent=self.name, key=f"scout:kick:{time.strftime('%Y-%m-%d')}",
                      title="Top Kick streamers live now", body=body, priority=LOW)]

    # --- clip pipeline ---------------------------------------------------------------------
    def _process_twitch(self, ctx: AgentContext, hdr: dict) -> list[Alert]:
        streamers = [s for s in (self.cfg.get("streamers") or []) if s.get("permission")]
        if not streamers:
            return []
        logins = [s["login"] for s in streamers]
        users = self.get_json(ctx.http, f"{HELIX}/users", headers=hdr, params=[("login", l) for l in logins])
        ids = {u["login"].lower(): u["id"] for u in users.get("data", [])}
        posted = set(ctx.store.get(self.name, "posted", []))
        since = (datetime.now(timezone.utc) - timedelta(hours=int(self.cfg.get("lookback_hours", 24))))
        out_dir = Path(self.cfg.get("output_dir", "data/clips"))
        alerts = []
        for s in streamers:
            bid = ids.get(s["login"].lower())
            if not bid:
                continue
            clips = self.get_json(ctx.http, f"{HELIX}/clips", headers=hdr, params={
                "broadcaster_id": bid, "started_at": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "first": 50}).get("data", [])
            for clip in pick_clips(clips, posted, int(self.cfg.get("min_views", 500)),
                                   int(self.cfg.get("max_clips_per_streamer", 2))):
                alerts.append(self._publish(ctx, clip, s, out_dir))
                posted.add(clip["id"])
        ctx.store.put(self.name, "posted", sorted(posted)[-5000:])
        return alerts

    def _publish(self, ctx: AgentContext, clip: dict, streamer: dict, out_dir: Path) -> Alert:
        title, desc, tags = caption_for(clip, streamer)
        results = []
        if ctx.dry_run or not (shutil.which("yt-dlp") and shutil.which("ffmpeg")):
            results.append("dry run / yt-dlp+ffmpeg missing: not downloaded")
        else:
            try:
                path = self._render(clip, out_dir)
                results.append(f"rendered {path}")
                if self.cfg.get("upload_youtube") and env("YT_REFRESH_TOKEN"):
                    results.append("YouTube: " + youtube_upload(ctx.http, str(path), title, desc, tags,
                                                                self.cfg.get("youtube_privacy", "public")))
                if self.cfg.get("upload_tiktok") and env("TIKTOK_ACCESS_TOKEN"):
                    tiktok_upload_draft(ctx.http, str(path))
                    results.append("TikTok: sent to your inbox as a draft - open the app to post")
            except Exception as e:
                results.append(f"FAILED: {e}")
        return Alert(agent=self.name, key=f"clip:{clip['id']}",
                     title=f"Clip ready: {clip['broadcaster_name']} - {clip['title'][:60]} ({clip['view_count']:,} views)",
                     body=f"Caption: {title}\n" + "\n".join(results),
                     priority=HIGH if clip["view_count"] >= 5000 else NORMAL, url=clip["url"],
                     data={"streamer": streamer["login"], "views": clip["view_count"]})

    def _render(self, clip: dict, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        raw, final = out_dir / f"{clip['id']}_raw.mp4", out_dir / f"{clip['id']}_vertical.mp4"
        subprocess.run(["yt-dlp", "-q", "-f", "best[ext=mp4]/best", "-o", str(raw), clip["url"]],
                       check=True, timeout=300)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter_complex", VERTICAL_FILTER,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                        "-movflags", "+faststart", str(final)], check=True, timeout=600)
        raw.unlink(missing_ok=True)
        return final

    def digest_section(self, alerts: list[dict]) -> str:
        clips = [a for a in alerts if a["key"].startswith("clip:")]
        if not clips:
            return "  no new clips (add approved streamers under agents.clipper.streamers)"
        by: dict[str, int] = {}
        for a in clips:
            by[a["data"]["streamer"]] = by.get(a["data"]["streamer"], 0) + 1
        return "  " + ", ".join(f"{k}: {v} clips" for k, v in by.items())
