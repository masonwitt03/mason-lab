# Beginner's Guide: Step by Step

This guide assumes you've never done any coding. Follow the steps in order.
Every command is in a gray box. Copy it exactly, paste it, and press **Enter**.

**What's in here**
- [Part 0: Set up your computer (do this first, once)](#part-0-set-up-your-computer-do-this-first-once)
- [Part 1: Get alerts on your phone](#part-1-get-alerts-on-your-phone)
- [Part 2: Sell the shirts I made (Etsy + Printify)](#part-2-sell-the-shirts-i-made-etsy--printify)
- [Part 3: Resell real vintage shirts (Depop)](#part-3-resell-real-vintage-shirts-depop)
- [Part 4: Clipping streamers (YouTube / TikTok)](#part-4-clipping-streamers-youtube--tiktok)
- [Part 5: Crypto alerts](#part-5-crypto-alerts)
- [Part 6: Alerts when famous people post coins on X](#part-6-alerts-when-famous-people-post-coins-on-x)
- [Part 7: Turn everything on](#part-7-turn-everything-on)
- [If something goes wrong](#if-something-goes-wrong)

**My advice:** start with **Part 0, Part 1 and Part 2** this week. Add one more part each week.
Don't try to set up everything in one day.

---

## Words you'll see

| Word | What it means |
|---|---|
| **Terminal** | A window where you type commands. On Mac it's called **Terminal**. On Windows use **PowerShell**. |
| **Command** | A line of text you paste into the terminal and run by pressing Enter. |
| **Folder** / **directory** | Same thing. |
| **API key** / **token** | A password that lets this program use a website (Etsy, Twitch...) for you. Never share these. |
| **`.env` file** | The file where your API keys go. |
| **`config.yaml`** | The settings file (what's on or off, prices, which streamers...). |

### Mac vs Windows

A few commands are different. When this guide says `python`, use the one for your computer:

| | Mac | Windows |
|---|---|---|
| Run Python | `python3` | `python` |
| Copy a file | `cp` | `copy` |

Everything else is the same.

---

## Part 0: Set up your computer (do this first, once)

### Step 0.1: Install Python

Python is the language the program is written in.

- **Mac:** go to https://www.python.org/downloads/, click the big yellow **Download Python** button, open the file and click through the installer.
- **Windows:** go to https://www.python.org/downloads/ and click **Download Python**. Open the file.
  **Important: on the first screen, check the box "Add python.exe to PATH"**, then click **Install Now**.

### Step 0.2: Install Git

Git downloads the project from GitHub.

- **Mac:** open Terminal (press `Cmd + Space`, type `Terminal`, press Enter), paste this and press Enter:
  ```
  xcode-select --install
  ```
  Click **Install** in the window that pops up.
- **Windows:** go to https://git-scm.com/download/win, download it, and click **Next** on every screen.

### Step 0.3: Open the terminal

- **Mac:** press `Cmd + Space`, type `Terminal`, press Enter.
- **Windows:** click Start, type `PowerShell`, press Enter.

### Step 0.4: Check that it worked

Paste this and press Enter (Windows: use `python` instead of `python3`):
```
python3 --version
```
You should see something like `Python 3.12.5`. If you get an error, restart your computer and try again.

### Step 0.5: Download the project

Paste these one at a time, pressing Enter after each:
```
cd ~
git clone https://github.com/masonwitt03/mason-lab.git
cd mason-lab
git checkout claude/multi-agent-ecommerce-streaming-trading-t2ib0o
```
If it asks you to log in to GitHub, log in with your GitHub account.

> **Every time you open a new terminal later**, run `cd ~/mason-lab` first so you're in the project folder.

### Step 0.6: Install the parts the program needs

Mac:
```
python3 -m pip install -r requirements.txt
```
Windows:
```
python -m pip install -r requirements.txt
```
Lots of text will scroll by. That's normal. Wait until it stops.

### Step 0.7: Make your settings files

Mac:
```
cp config.example.yaml config.yaml
cp .env.example .env
```
Windows:
```
copy config.example.yaml config.yaml
copy .env.example .env
```

### Step 0.8: Learn how to open and edit these files

You'll edit `config.yaml` and `.env` a lot. Open them in a plain text editor:

- **Mac:** `open -e config.yaml` (and `open -e .env`)
- **Windows:** `notepad config.yaml` (and `notepad .env`)

Rules for editing:
- In `.env`, put your key right after the `=` with **no spaces**. Example: `PRINTIFY_TOKEN=abc123xyz`
- In `config.yaml`, **spacing at the start of lines matters.** Only change the value after the `:`. Don't move lines left or right.
- Always **save** (`Cmd+S` / `Ctrl+S`) after editing.

✅ **Part 0 done.**

---

## Part 1: Get alerts on your phone

The program sends everything (hot coins, clips, price-cut reminders) to your phone through a free app called **ntfy**.

1. Install **ntfy** on your phone (App Store or Google Play).
2. Open it and tap **+** (Subscribe to topic).
3. Make up a topic name nobody could guess, like `mason-lab-k8x2q9` (anyone who knows the name can read your alerts). Type it and tap **Subscribe**.
4. On your computer, open `.env` (see Step 0.8) and change the `NTFY_TOPIC` line to your topic:
   ```
   NTFY_TOPIC=mason-lab-k8x2q9
   ```
   Save the file.
5. Send yourself a test alert:
   ```
   python3 -m mason_lab test-notify
   ```
   Your phone should buzz with **"Mason Lab test"**. 🎉

✅ **Part 1 done.**

---

## Part 2: Sell the shirts I made (Etsy + Printify)

**How this works:** you never touch a shirt. A customer buys on Etsy, then **Printify** prints the design on a shirt and ships it to them.
You keep the difference between your Etsy price and Printify's cost (usually about **$8 to $12 profit per shirt**).

### Step 2.1: Look at the designs

I already made **18 designs**. They're in the `shirts` folder.
- `shirts/PREVIEW.jpg` shows all of them on shirts.
- Each design has its own folder with:
  - `print.png` = the file the printer uses (high quality, see-through background)
  - `mockup.jpg` = a preview picture
  - `design.json` = a ready-made Etsy title, tags and description

To see them, open the `shirts` folder:
- **Mac:** `open shirts`
- **Windows:** `explorer shirts`

### Step 2.2: Make your own designs (optional)

Put your own last name and hometown in:
```
python3 -m mason_lab shirts collection --surname JOHNSON --town NASHVILLE --year 1996
```
The new files go in `data/designs`.

Make a single custom design:
```
python3 -m mason_lab shirts make nashville_tee --template arch --palette cream_on_navy --top NASHVILLE --main ATHLETICS --est "EST. 1806"
```
See all the layouts and color choices:
```
python3 -m mason_lab shirts options
```

**The four layouts:**
- `arch`: curved word on top, big word, "EST. year". Use `--top`, `--main` and `--est`.
- `dept`: "PROPERTY OF / NAME / ATHLETIC DEPT.". Use `--top`, `--main` and `--sub`.
- `gameday`: "GAME 🏈 DAY" plus a small line. Use `--main`, `--sub` and `--tag`.
- `badge`: a round badge. Use `--top`, `--bottom` and `--main`.

> ⚠️ The program **refuses** college names (Texas, Michigan...) and brands (Disney, Nike...).
> Putting those on shirts you make is illegal without a license, and Etsy shuts down shops for it.
> The **Game Day** shirts come in team colors with no names, so fans still buy them for their team.

### Step 2.3: Open an Etsy shop

1. Go to https://www.etsy.com/sell and click **Get started**.
2. Choose a shop name, and set up payments (your bank account) and billing.
3. Etsy charges **$0.20 per listing**, plus about 10% when something sells.
4. You'll need at least one listing to finish opening the shop. That listing will come from Printify in Step 2.7.

### Step 2.4: Make a Printify account and connect it to Etsy

1. Go to https://printify.com and sign up (free).
2. Click **Manage my stores** (top right), then **Add new store**, then **Etsy**, then **Connect**. Log in to Etsy and click **Allow access**.

### Step 2.5: Get your Printify token

1. In Printify, click your profile (top right), then **Connections**.
2. Under **API tokens**, click **Generate**. Name it `mason-lab`, choose **All scopes**, and click **Generate token**.
3. Copy the long token. Open `.env` and paste it:
   ```
   PRINTIFY_TOKEN=paste-the-long-token-here
   ```
   Save.

### Step 2.6: Tell the program which shop and which shirt to use

Run:
```
python3 -m mason_lab shirts printify-setup
```
You'll see lines like:
```
Shop: MyEtsyShop  id=12345678  (etsy)
Shirt: Unisex Garment-Dyed T-shirt (Comfort Colors 1717)  blueprint_id=706
```
1. Open `config.yaml` and find the `designs:` section.
2. Copy the shop `id` number next to `printify_shop_id:`.
3. Copy the `blueprint_id` next to `printify_blueprint_id:`. I recommend the **Comfort Colors 1717**: it's the soft, washed-out vintage tee that sells best on Etsy right now.
4. Save, then run the same command again:
   ```
   python3 -m mason_lab shirts printify-setup
   ```
   Now it also lists printers (`provider_id=...`). Pick one in the US and put its number next to `printify_provider_id:`. Save.

When you're done, that part of `config.yaml` should look something like this (with your own numbers):
```
  price: 29.99
  printify_shop_id: 12345678
  printify_blueprint_id: 706
  printify_provider_id: 99
```

### Step 2.7: Upload a design

Upload the red and black Game Day shirt:
```
python3 -m mason_lab shirts upload gameday_red_black
```
(It finds designs in both the `shirts` folder and `data/designs`, where your own designs go.)

Then:
1. Go to Printify, then **My Products**. The shirt is there as a **draft**.
2. Click it. Check the preview pictures, and move or resize the design if you want.
3. Click **Publish**. It now shows up on your Etsy shop. 🎉
4. Do the same for the other designs (the names are the folder names in `shirts`).

To use a different price for one design:
```
python3 -m mason_lab shirts upload coffee_club --price 32.99
```

### Step 2.8: When someone orders

- **Normal shirts:** Printify prints and ships them automatically. You don't do anything. (Printify charges your card for the shirt when the order comes in.)
- **Personalized shirts** (the family name, hometown and bachelorette ones): the buyer types their name. You then:
  1. Make their version:
     ```
     python3 -m mason_lab shirts make order_4821 --template dept --palette navy_on_ivory --main GARCIA
     ```
  2. In Printify, open the order and swap in the new `print.png` from `data/designs/order_4821` before it goes to print.

### Step 2.9: Tips to actually get sales

- Upload **all 10 Game Day colors** now. It's football season, and these sell until January.
- Use the **title and tags** from each design's `design.json`. They're written for Etsy search.
- Make your first listing photo a **Printify mockup** (they look real). Use my `mockup.jpg` as an extra photo.
- 10 to 20 listings is a good start. More listings means more chances to show up in search.

✅ **Part 2 done.**

---

## Part 3: Resell real vintage shirts (Depop)

This is for **real old shirts** you buy at thrift stores and resell. These can have college names, because they're genuine, officially licensed shirts.

### Step 3.1: Set up Depop

Download the **Depop** app, sign up, and set up your shop and payments.

### Step 3.2: Every time you buy a shirt

Type a quick description and what you paid:
```
python3 -m mason_lab vintage add "90s Champion Michigan tee, L, small stain" --cost 4
```
It gives you:
- a **title**, a **Depop description** and **hashtags**. Copy and paste them into the Depop app.
- a **suggested price**
- a **number** for that shirt (like `#1`). You'll need it when it sells.

If you measured it, add the measurements (inches):
```
python3 -m mason_lab vintage add "80s Notre Dame crewneck XL" --cost 6 --p2p 22 --length 28
```
(`p2p` = armpit to armpit across the front)

### Step 3.3: When a shirt sells

Use the shirt's number and the price it sold for:
```
python3 -m mason_lab vintage sold 1 32
```
Sold on eBay and paid $5 shipping?
```
python3 -m mason_lab vintage sold 2 55 --platform ebay --shipping 5
```

### Step 3.4: Other handy commands

| What you want | Command |
|---|---|
| See everything that's listed | `python3 -m mason_lab vintage list` |
| See your profit and best sellers | `python3 -m mason_lab vintage stats` |
| Change a price (shirt #3 to $29.99) | `python3 -m mason_lab vintage price 3 29.99` |
| Show the listing text again | `python3 -m mason_lab vintage listing 3` |

**Automatic:** once the system is running (Part 7), your phone gets told which shirts to discount, and every Sunday you get a report on what's making you the most money.

✅ **Part 3 done.**

---

## Part 4: Clipping streamers (YouTube / TikTok)

The program finds each streamer's most-viewed clips from the last day, makes them vertical (for Shorts and TikTok), and uploads them with credit.

> ⚠️ **Only clip streamers who allow it.** Many big streamers run **clipping programs**, and some pay you per view.
> Look for a "clipper" channel in their Discord, or search "[streamer name] clipping program".
> Clipping people without permission gets your channels taken down.

### Step 4.1: Install ffmpeg (it edits the videos)

- **Mac:** install Homebrew from https://brew.sh (copy the command on that page into Terminal). Then run:
  ```
  brew install ffmpeg
  ```
- **Windows:**
  ```
  winget install Gyan.FFmpeg
  ```
  Then close PowerShell and open it again.

### Step 4.2: Get Twitch keys

1. Go to https://dev.twitch.tv/console and log in with your Twitch account.
2. Click **Register Your Application** and fill it in:
   - Name: `mason-lab-yourname`
   - OAuth Redirect URL: `http://localhost`
   - Category: **Application Integration**
   - Client Type: **Confidential**
   Then click **Create**.
3. Click **Manage**. Copy the **Client ID**. Click **New Secret** and copy the secret.
4. Put both in `.env`:
   ```
   TWITCH_CLIENT_ID=your-client-id
   TWITCH_CLIENT_SECRET=your-secret
   ```

### Step 4.3: Add the streamers you're allowed to clip

Open `config.yaml` and find `streamers:` under `clipper:`. Add one line per streamer (use their Twitch username).
It must be indented exactly like this:
```
    streamers:
      - {login: streamername, permission: true, hashtags: [streamername, twitch, fyp]}
      - {login: anotherstreamer, permission: true}
```

### Step 4.4: Test it (without uploading yet)

```
python3 -m mason_lab once clipper
```
Your finished vertical videos appear in `data/clips`.
**Easiest way to post:** send them to your phone (AirDrop, Google Drive...) and upload them in the TikTok and YouTube apps.

### Step 4.5: Automatic YouTube uploads (optional, about 20 minutes)

1. Go to https://console.cloud.google.com, click **Select a project**, then **New Project**. Name it `mason-lab` and click **Create**.
2. In the search bar, type **YouTube Data API v3**, open it, and click **Enable**.
3. Go to **APIs & Services**, then **OAuth consent screen**:
   - choose **External**, fill in the app name and your email, and click Save through each page
   - under **Test users**, add your own Gmail address
4. Go to **APIs & Services**, then **Credentials**, then **Create Credentials**, then **OAuth client ID**. Choose **Desktop app** and click **Create**.
5. Copy the **Client ID** and **Client Secret** into `.env`:
   ```
   YT_CLIENT_ID=...
   YT_CLIENT_SECRET=...
   ```
6. Run this. It opens your browser; log in and click **Allow** (if Google says the app isn't verified, click **Continue**):
   ```
   python3 -m mason_lab youtube-auth
   ```
7. It prints a line starting with `YT_REFRESH_TOKEN=`. Copy that whole line into `.env`.
8. In `config.yaml`, under `clipper:`, change `upload_youtube: false` to `upload_youtube: true`.

YouTube lets this upload about **6 videos a day**.

**TikTok:** automatic TikTok posting needs a TikTok developer app that TikTok has to approve, which is hard as a beginner. **Just upload the videos from `data/clips` in the TikTok app.** It takes 30 seconds each.

✅ **Part 4 done.**

---

## Part 5: Crypto alerts

This one works right away. No keys needed.

### Step 5.1: Set your budget

Open `config.yaml` and find `crypto:`. Change:
- `bankroll_usd: 500` to the total amount you're willing to **lose completely**
- `risk_per_trade_pct: 2` = the most you'll lose on any single coin, as a percentage of that amount

### Step 5.2: Try it

```
python3 -m mason_lab once crypto
```

### Step 5.3: How to read an alert

```
🚀 $PUMP momentum 78/100 (+80% 1h)
Price $0.0012 | 5m +12% | 1h +80% | 6h +150%
MC $1,200,000 | Liq $150,000 | Vol 1h $300,000 (x3 accel) | buys 75%
CA: 7xKX...
Max size $33 (risking $10) | stop -30% @ 0.00084 | take 1/2 at +100% @ 0.0024
```
- **momentum**: 0 to 100. Higher means it's rising faster right now.
- **Liq** (liquidity): how much money is in the trading pool. Under $50k is risky, because it's easy for the price to crash.
- **buys 75%**: 75% of recent trades were buys.
- **CA**: the coin's address. Copy it into your wallet app (like Phantom) to find the exact coin, **not** a fake with the same name.
- **Max size**: the most to put in. **stop**: sell if it drops to this price. **take 1/2**: sell half if it doubles.
- **⚠️ instead of 🚀** means there are red flags listed. Be extra careful, or skip it.

> **Please read:** most coins that pump fast go to zero, often within hours. No tool can tell you which ones will keep going up.
> Only use money you can afford to lose, always follow the stop, and never put in more than the "Max size".

✅ **Part 5 done.**

---

## Part 6: Alerts when famous people post coins on X

> 💰 This needs a **paid X API plan** (X charges for reading posts). Skip this part until your other income covers it.

1. Go to https://developer.x.com, sign up, and choose a plan that allows reading posts.
2. In your app's **Keys and tokens** page, copy the **Bearer Token** into `.env`:
   ```
   X_BEARER_TOKEN=...
   ```
3. In `config.yaml`, under `x_watch:`, set `enabled: true` and list the accounts:
   ```
    x_watch:
      enabled: true
      interval_minutes: 2
      accounts: [elonmusk, someoneelse]
   ```
4. Try it:
   ```
   python3 -m mason_lab once x_watch
   ```
   The first run only remembers where it left off. Alerts start with their **next** posts.

> Remember: when a famous account posts a coin, it's often a paid ad. The people who bought early usually sell to everyone rushing in.

✅ **Part 6 done.**

---

## Part 7: Turn everything on

Start the whole system:
```
python3 -m mason_lab run
```
- **Leave this window open.** The system only runs while it's open and your computer is on (and not asleep).
- To stop it, click the window and press `Ctrl + C`.
- Every morning at 9am you get a **daily briefing** on your phone.

**Keep your computer awake:**
- **Mac:** System Settings, then **Lock Screen**, then set "Turn display off" to **Never** (or run `caffeinate -i python3 -m mason_lab run` instead).
- **Windows:** Settings, then **System**, then **Power**, then set "Sleep" to **Never**.

**Later:** to keep it running 24/7 without your computer, rent a small cloud server (about $5/month, from DigitalOcean or Hetzner) and repeat Part 0 on it.

### Getting updates I make to the program

```
cd ~/mason-lab
git pull
```

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `python3: command not found` (Mac) or `python is not recognized` (Windows) | Reinstall Python (Step 0.1). On Windows, check **"Add python.exe to PATH"**. Restart the computer. |
| `No module named ...` | Run Step 0.6 again. |
| `config.yaml not found` | You're not in the project folder. Run `cd ~/mason-lab` first. |
| Phone doesn't buzz | Check that `NTFY_TOPIC` in `.env` exactly matches the topic in the app, with no spaces. Run `test-notify` again. |
| `401` or `403` error | That API key is wrong or expired. Copy it again into `.env`. |
| `yaml` error after editing `config.yaml` | You moved a line's spacing. Compare it with `config.example.yaml` and match the indentation. |
| `agent 'x' is not enabled` | In `config.yaml`, set `enabled: true` for that part. |
| Anything else | Copy the whole error message and send it to me. |

## Keep these private

- **Never share your `.env` file** or post screenshots of it. It has your passwords.
- The program already keeps `.env` and `config.yaml` from ever being uploaded to GitHub.
