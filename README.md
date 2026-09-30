# Mason Lab

One central controller that runs five agents and pushes their findings to your phone.

```
                     ┌──────────────── Controller ────────────────┐
                     │ schedules agents · dedupes · daily briefing │
                     └──┬─────────┬──────────┬──────────┬─────────┘
                        │         │          │          │
            vintage · etsy   clipper     crypto     x_watch
                        │         │          │          │
                        └─────────┴────┬─────┴──────────┘
                                 ntfy (phone) · Discord · Telegram
```

| Agent | What it does | Default cadence |
|---|---|---|
| **vintage** | Your vintage reselling shop (Depop first, eBay/Etsy as extra channels). You log what you buy and sell; it writes listing copy, estimates fees, tracks profit, tells you which pieces need a price cut, and sends a Sunday report on which schools, brands and decades make you the most so you know what to buy. | daily check, weekly report |
| **etsy** *(off by default)* | Scores Etsy niches by demand (favorites/day on top listings) vs competition, drafts listings (title, 13 tags, price) for the best ones, and alerts on demand spikes. Filters out trademark-risk niches. | daily |
| **clipper** | Pulls the day's most-viewed Twitch clips from streamers **you're approved to clip**, renders 9:16 with blurred background, uploads to YouTube Shorts and sends to your TikTok drafts, with credit. Also scouts top live streamers on Twitch and Kick. | every 3h |
| **crypto** | Scans DexScreener (boosted + new tokens) and CoinGecko trending, scores momentum 0–100, lists red flags (thin liquidity, brand-new pair, RugCheck danger...), and gives a position size + stop for your bankroll. | every 5 min |
| **x_watch** | Watches X accounts you list; when one posts a contract address or `$TICKER`, it alerts with live DEX numbers. | every 2 min |

## Vintage reselling (Depop / eBay / Etsy)

Depop has no public API, so you log pieces yourself. Each command takes a few seconds:

```bash
# bought a shirt: writes the title, Depop description + hashtags, eBay title, Etsy tags and a starting price
python -m mason_lab vintage add "90s Champion Michigan tee, L, small stain" --cost 4 --p2p 21 --length 28

python -m mason_lab vintage list                 # what's listed, price, days listed
python -m mason_lab vintage sold 1 32            # sold #1 for $32 on Depop (fees estimated)
python -m mason_lab vintage sold 2 55 --platform ebay --shipping 5
python -m mason_lab vintage price 3 29.99        # after a markdown
python -m mason_lab vintage stats                # profit, ROI, sell-through, best schools/brands/decades
python -m mason_lab vintage listing 3            # reprint listing copy
```

It detects school (and adds the mascot, since buyers search both), brand, decade, size, type, events like "national champions", single stitch, and flaws. Anything it misses can be passed as a flag (`--school`, `--decade`, `--size`...). Suggested prices are a starting point; once you've logged sales, the weekly report shows what actually sells.

Resell **authentic** vintage only. Licensed shirts are legal to resell, but printing new shirts with college logos is trademark infringement and gets listings pulled and accounts banned.

The Etsy agent is still included as a second option for print-on-demand or digital products (`agents.etsy.enabled: true`).

## Setup

```bash
pip install -r requirements.txt        # plus ffmpeg for clipping: apt install ffmpeg / brew install ffmpeg
cp config.example.yaml config.yaml     # choose agents, thresholds, streamers, accounts
cp .env.example .env                   # API keys (only for what you enable)
python -m mason_lab test-notify        # confirm your phone gets it
python -m mason_lab once crypto        # try one agent
python -m mason_lab run                # start everything (keep running on a VPS / always-on PC)
```

**Phone alerts:** install the free [ntfy](https://ntfy.sh) app, subscribe to a hard-to-guess topic name, and put it in `NTFY_TOPIC`. Set `min_priority` so only high/urgent alerts buzz your phone; send the full feed to Discord.

**Keys you'll need** (all free unless noted): Etsy developer key · Twitch app (dev.twitch.tv) · Kick app (optional) · Google Cloud project with YouTube Data API v3 + an OAuth refresh token · TikTok developer app with `video.upload` · X API bearer token (reading timelines needs a **paid** X tier).

Data (sent alerts, run history, rendered clips) lives in `data/`. Run tests with `python -m pytest`.

## Ground rules built into the system

- **Crypto alerts are signals, not predictions.** Most fast-pumping tokens, and most coins shilled by big X accounts, go to zero; influencer posts are often paid promos, and the early buyers sell to followers. The bot never trades for you. It sizes every alert so a stop-out only costs `risk_per_trade_pct` of the bankroll you set, and halves the size when there are red flags. Only use money you can afford to lose entirely.
- **Only clip streamers who've said yes.** Reposting someone's stream without permission gets channels struck and demonetized. Many big streamers run clipping programs (often paid per view); join those, then add the streamer with `permission: true`. Everyone else only appears in the scouting report.
- **Etsy listings are drafts.** You add your own product photos and publish yourself. Niches with brand/character names are filtered out because they get shops closed.

## Tuning for results

- Crypto: raise `min_score` or set `hide_flagged: true` if you get too many alerts; lower `min_liquidity_usd` to catch coins earlier (with more rug risk).
- Clipping: YouTube's default API quota allows about 6 uploads/day. Post the highest-view clips first (the agent already does), and keep 1–2 streamers per channel so your audience stays focused.
- Etsy: add your own `seed_keywords`. The weekly report shows demand trends against the previous scan, so niches that are climbing stand out.
