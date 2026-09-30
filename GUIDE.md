# Beginner's Guide: Step by Step

This guide assumes you've never done any coding. Follow the steps in order, one at a time.
When you see a gray box, copy what's inside it exactly, paste it, and press **Enter**.

**What's in here**
- [Part 0: Set up your computer (once, about 15 minutes)](#part-0-set-up-your-computer-once-about-15-minutes)
- [Part 1: Start it (double-click)](#part-1-start-it-double-click)
- [Part 2: Sell the holiday shirts (Etsy + Printify)](#part-2-sell-the-holiday-shirts-etsy--printify)
- [Part 3: Resell real vintage shirts (Depop)](#part-3-resell-real-vintage-shirts-depop)
- [Part 4: Clipping streamers (YouTube / TikTok)](#part-4-clipping-streamers-youtube--tiktok)
- [Part 5: Crypto alerts](#part-5-crypto-alerts)
- [Part 6: Alerts when famous people post coins on X](#part-6-alerts-when-famous-people-post-coins-on-x)
- [Part 7: Keep it running](#part-7-keep-it-running)
- [If something goes wrong](#if-something-goes-wrong)

**My advice:** do **Parts 0, 1 and 2 this week**, because the holiday shirts need to be up before Halloween.
Add one more part each week after that.

---

## Words you'll see

| Word | What it means |
|---|---|
| **Terminal** | A window where you type commands. On Mac it's the app called **Terminal**. On Windows it's **PowerShell**. |
| **Command** | A line of text you paste into the terminal, then press Enter to run it. |
| **API key** / **token** | A password that lets this program use a website (Printify, Twitch...) for you. Never share these. |
| **Settings files** | `config.yaml` (your choices) and `.env` (your passwords). The setup helper fills these in for you. |

### Mac vs Windows

When a command in this guide starts with `python3` and you're on **Windows**, type `python` instead. Everything else is the same.

---

## Part 0: Set up your computer (once, about 15 minutes)

### Step 0.1: Install Python

Python is the language the program is written in. You install it once, like any other app.

1. Go to https://www.python.org/downloads/
2. Click the big yellow **Download Python** button.
3. Open the file you downloaded.
   - **Windows:** on the first screen, **check the box "Add python.exe to PATH"** at the bottom. This is important. Then click **Install Now**.
   - **Mac:** click **Continue** / **Agree** / **Install** until it's done. When a folder opens at the end, double-click **Install Certificates.command** inside it.

### Step 0.2: Download the project

1. Go to https://github.com/masonwitt03/mason-lab and log in if it asks.
2. Near the top left there's a button that says **main** (the branch picker). Click it and choose **claude/multi-agent-ecommerce-streaming-trading-t2ib0o**.
3. Click the green **Code** button, then **Download ZIP**.
4. Find the ZIP in your **Downloads** folder and double-click it to unzip it. (**Windows:** right-click it and choose **Extract All**, then click **Extract**.)
5. Move the unzipped folder somewhere easy, like your **Desktop**, and rename it to `mason-lab`.

✅ **Part 0 done.** You won't need to repeat it.

---

## Part 1: Start it (double-click)

### Step 1.1: Get the phone app ready

1. On your phone, install **ntfy** (free, from the App Store or Google Play).
2. Open it. Don't subscribe to anything yet. The setup helper will give you a name to type in.

### Step 1.2: Double-click the start file

Open your `mason-lab` folder:
- **Mac:** double-click **Start-Mac.command**.
  - If your Mac says it **can't be opened** or "Apple could not verify" it: click **Done** (not "Move to Trash").
    Then open **System Settings**, click **Privacy & Security**, and scroll down until you see a message about "Start-Mac.command". Click **Open Anyway**, then type your Mac password.
    Double-click the file again and click **Open**. You only do this the first time.
- **Windows:** double-click **Start-Windows.bat**.
  - If a blue box says "Windows protected your PC": click **More info**, then **Run anyway**.

A window with text opens. The first time, it spends a minute installing what it needs, then the **setup helper** starts.

### Step 1.3: Answer the setup questions

The helper asks 4 questions. Type your answer and press **Enter**. To skip one for now, just press **Enter**.

1. **Phone alerts:** it shows you a topic name, like `mason-lab-k8x2q9`.
   - On your phone, in ntfy, tap **+**, type that exact name and tap **Subscribe**.
   - Back on the computer, press **Enter** to keep that name.
   - When it asks to send a test, type `y` and press Enter. **Your phone should buzz.** 🎉
2. **Printify token:** press **Enter** to skip for now. You'll get it in Part 2, then run the setup again.
3. **Crypto money:** type the most you're OK losing completely, like `200`.
4. **Twitch:** press **Enter** to skip for now (Part 4).

After the questions, it says **"Mason Lab is running."** That's it. It now works in the background and sends updates to your phone.

- **To stop it:** close that window.
- **To start it again later:** double-click the start file again. It skips the questions after the first time.
- **To change your answers later**, open the terminal in the project folder and run the setup again (see "How to open a terminal in the project folder" below):
  ```
  python3 -m mason_lab setup
  ```

### How to open a terminal in the project folder

You'll need this for a few commands in the next parts.
- **Mac:** open the **Terminal** app (press `Cmd + Space`, type `Terminal`, press Enter). Type `cd ` (with a space after it), **drag your `mason-lab` folder into the Terminal window**, and press Enter.
- **Windows:** open your `mason-lab` folder, click the address bar at the top, type `powershell` and press Enter.

✅ **Part 1 done.**

---

## Part 2: Sell the holiday shirts (Etsy + Printify)

**How this works:** you never touch a shirt. A customer buys on Etsy, then **Printify** prints the design on a shirt and ships it to them.
You keep the difference between your price and Printify's cost. With these shirts at $29.99 that's usually about **$10–13 per shirt**.

### Step 2.1: Look at the designs

Open the `shirts` folder inside `mason-lab`. **`PREVIEW.jpg`** shows all 11:

| When to sell | Designs |
|---|---|
| **Halloween (list now, sells until about Oct 25)** | Spooky Season, Boo Crew *(personalized family name)* |
| **Fall and Thanksgiving (Oct and Nov)** | Hey Pumpkin, Cozy Season, Thankful |
| **Christmas (mid-Nov to mid-Dec is Etsy's busiest time)** | Merry & Bright, Holly Jolly, Family Christmas *(personalized, red or cream shirt)*, Oh Snap! gingerbread, Christmas Tree Farm |

Each design has its own folder with 3 files:
- `print.png`: the file the printer uses (high quality, see-through background)
- `mockup.jpg`: a preview picture of the shirt
- `design.json`: the ready-made Etsy **title**, **13 tags** and **description**. You can open it with Notepad or TextEdit.

All of them are designed for the **Comfort Colors 1717** shirt, the soft, washed-looking tee that's trending on Etsy right now.

### Step 2.2: Open an Etsy shop

1. Go to https://www.etsy.com/sell and click **Get started**.
2. Choose a shop name, and set up how you get paid (your bank account) and billing.
3. Etsy charges **$0.20 per listing**, plus about 10% when something sells.
4. Etsy wants one listing before your shop opens. That listing will come from Printify in Step 2.6.

### Step 2.3: Make a Printify account and connect it to Etsy

1. Go to https://printify.com and sign up (it's free).
2. Click **Manage my stores** (top right), then **Add new store**, then **Etsy**, then **Connect**.
3. Log in to Etsy and click **Allow access**.

### Step 2.4: Get your Printify token and give it to the program

1. In Printify, click your profile picture (top right), then **Connections**.
2. Under **API tokens**, click **Generate**. Name it `mason-lab`, choose **All scopes**, and click **Generate token**.
3. **Copy** the long token.
4. Open a terminal in the project folder (see Part 1) and run:
   ```
   python3 -m mason_lab setup
   ```
   Press Enter to keep your phone answers. At the **Printify token** question, paste the token and press Enter.
   It should say **"Connected to your shop"**.

### Step 2.5: Choose the shirt and the printer (one time)

1. In the terminal, run:
   ```
   python3 -m mason_lab shirts printify-setup
   ```
2. Find the line with **Comfort Colors 1717** and note its `blueprint_id` number.
3. Open `config.yaml` (Mac: `open -e config.yaml`, Windows: `notepad config.yaml`). Find the line `printify_blueprint_id:` and type the number after it, with a space after the colon. For example: `printify_blueprint_id: 706`. Save (`Cmd+S` / `Ctrl+S`).
4. Run the same command again:
   ```
   python3 -m mason_lab shirts printify-setup
   ```
   Now it also lists **printers**. Pick one in the United States and put its number after `printify_provider_id:` in `config.yaml`, the same way. Save.

### Step 2.6: Upload the shirts

Upload the first one:
```
python3 -m mason_lab shirts upload spooky_season
```
Then:
1. In Printify, go to **My Products**. The shirt is there as a **draft**.
2. Click it and look at the preview photos. Drag the design up or down if you want.
3. Click **Publish**. It now appears in your Etsy shop. 🎉

Do the same for the others. Replace `spooky_season` with each folder name:
```
python3 -m mason_lab shirts upload boo_crew
python3 -m mason_lab shirts upload hey_pumpkin
python3 -m mason_lab shirts upload cozy_season
python3 -m mason_lab shirts upload thankful
python3 -m mason_lab shirts upload merry_and_bright
python3 -m mason_lab shirts upload holly_jolly
python3 -m mason_lab shirts upload family_christmas_red
python3 -m mason_lab shirts upload family_christmas_ivory
python3 -m mason_lab shirts upload oh_snap
python3 -m mason_lab shirts upload christmas_tree_farm
```

### Step 2.7: Turn on personalization (for Boo Crew and Family Christmas)

In Etsy, open each of those 3 listings, click **Edit**, scroll to **Personalization**, turn it on, and type the instructions:
`Type your family name exactly as you want it printed (and the year, if different).`

### Step 2.8: When someone orders

- **Normal shirts:** Printify prints and ships them automatically. You don't do anything.
- **Personalized shirts:** read the name the buyer typed in the Etsy order (say, "Garcia"). Then:
  1. Make their version with one command:
     ```
     python3 -m mason_lab shirts personalize family_christmas_red --name Garcia
     ```
     It tells you where it saved the new file.
  2. In Printify, open **Orders**, click that order, and choose **Edit**. Replace the design with the new `print.png` file, then **Save**.
  3. Do this within a few hours of the order, before it goes to print.

### Step 2.9: Tips to get sales

- **List the Halloween shirts first, today if you can.** Halloween sales stop around Oct 25.
- Use the **title and tags** from each `design.json`. They're written for Etsy search.
- Make your first photo a **Printify mockup** (they look like real photos). Add my `mockup.jpg` as an extra photo.
- Around **Nov 1**, lower the Halloween listings and focus on the Christmas ones. The **Family Christmas** shirts will likely be your best sellers, because families buy several at once.

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
4. Easiest: run `python3 -m mason_lab setup` and paste them when it asks. Or put both in `.env` (Mac: `open -e .env`, Windows: `notepad .env`), right after the `=` with no spaces, then save:
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

## Part 7: Keep it running

The program only works while its window is open **and** your computer is on.

- **Start it:** double-click **Start-Mac.command** or **Start-Windows.bat**.
- **Stop it:** close the window.
- **Keep your computer from sleeping:**
  - **Mac:** the start file already keeps your Mac awake while it runs. Just keep it plugged in, with the lid open.
  - **Windows:** Settings, then **System**, then **Power**, then set "Sleep" to **Never** (when plugged in).
- **Every morning at 9am** you get a **daily briefing** on your phone.

**Later, when it's making money:** you can run it 24/7 without your own computer by renting a small online computer (a "VPS") for about $5/month from DigitalOcean or Hetzner. Ask me when you're ready, and I'll walk you through it.

### Getting new versions I make

Download the ZIP again (Step 0.2) and copy your `config.yaml` and `.env` files from the old folder into the new one.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `python3: command not found` (Mac) or `python is not recognized` (Windows) | Reinstall Python (Step 0.1). On Windows, check **"Add python.exe to PATH"**. Restart the computer. |
| `No module named ...` | Double-click the start file again. It installs what's missing. |
| `config.yaml not found` | Your terminal isn't in the project folder. See "How to open a terminal in the project folder" in Part 1. |
| Phone doesn't buzz | Run `python3 -m mason_lab setup` again and make sure the topic name matches the one in the ntfy app **exactly**. |
| `401` or `403` error | That API key is wrong or expired. Copy it again into `.env`. |
| `yaml` error after editing `config.yaml` | You moved a line's spacing. Compare it with `config.example.yaml` and match the indentation. |
| `agent 'x' is not enabled` | In `config.yaml`, set `enabled: true` for that part. |
| Anything else | Copy the whole error message and send it to me. |

## Keep these private

- **Never share your `.env` file** or post screenshots of it. It has your passwords.
- The program already keeps `.env` and `config.yaml` from ever being uploaded to GitHub.
