#!/usr/bin/env python3
"""
Daily Finance Brief Generator
Fetches news from RSS feeds and generates HTML using Anthropic API.
Runs daily via GitHub Actions at 9 AM IST.
"""

import os
import sys
import time
import feedparser
from datetime import datetime, timedelta
import anthropic

# ---------------------------------------------------------------------------
# RSS Feed sources — Indian finance + global markets
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    {"url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",      "source": "Economic Times"},
    {"url": "https://economictimes.indiatimes.com/economy/rssfeeds/1373380680.cms",      "source": "Economic Times Economy"},
    {"url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",  "source": "ET Markets"},
    {"url": "https://www.moneycontrol.com/rss/latestnews.xml",                           "source": "MoneyControl"},
    {"url": "https://www.business-standard.com/rss/markets-106.rss",                    "source": "Business Standard"},
    {"url": "https://www.financialexpress.com/market/feed/",                             "source": "Financial Express"},
    {"url": "https://www.livemint.com/rss/markets",                                      "source": "LiveMint"},
    {"url": "https://www.firstpost.com/rss/business.xml",                               "source": "Firstpost Business"},
    {"url": "https://feeds.reuters.com/reuters/businessNews",                            "source": "Reuters Business"},
    {"url": "https://feeds.reuters.com/reuters/INbusinessNews",                          "source": "Reuters India"},
    {"url": "https://www.ndtv.com/business/feeds",                                       "source": "NDTV Profit"},
    {"url": "https://www.thehindu.com/business/Economy/?service=rss",                   "source": "The Hindu Business"},
    {"url": "https://www.businesstoday.in/rssfeeds/1260968891.cms",                      "source": "Business Today"},
]


def fetch_feed(feed_info: dict) -> list:
    """Fetch and parse a single RSS feed, return list of article dicts."""
    try:
        feed = feedparser.parse(
            feed_info["url"],
            request_headers={"User-Agent": "DailyFinanceBriefBot/2.0"}
        )
        articles = []
        for entry in feed.entries[:12]:
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            # strip HTML tags from summary
            import re
            summary = re.sub(r"<[^>]+>", " ", summary)
            summary = re.sub(r"\s+", " ", summary).strip()[:400]
            link    = entry.get("link", "")
            pub     = entry.get("published", entry.get("updated", ""))
            if title and link:
                articles.append({
                    "title":   title,
                    "summary": summary,
                    "link":    link,
                    "published": pub,
                    "source":  feed_info["source"],
                })
        return articles
    except Exception as exc:
        print(f"  WARN: Could not fetch {feed_info['source']}: {exc}")
        return []


def build_articles_block(articles: list) -> str:
    """Format articles into a readable block for the Claude prompt."""
    lines = []
    for i, art in enumerate(articles, 1):
        lines.append(f"[{i}] SOURCE: {art['source']}")
        lines.append(f"    TITLE: {art['title']}")
        if art["summary"]:
            lines.append(f"    SUMMARY: {art['summary']}")
        lines.append(f"    URL: {art['link']}")
        if art["published"]:
            lines.append(f"    DATE: {art['published']}")
        lines.append("")
    return "\n".join(lines)


def generate_html(articles_block: str, today: str) -> str:
    """Call Anthropic API with the news articles and return the full HTML page."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are generating "The Daily Finance Brief" for Sourabh — a personalized morning finance news digest.
Today's date: {today}

Below are news articles collected from RSS feeds. Use them to build the brief.

=== NEWS ARTICLES ===
{articles_block}
=== END ARTICLES ===

Generate a COMPLETE self-contained HTML page (<!DOCTYPE html> through </html>) for "The Daily Finance Brief".
Output ONLY raw HTML — no markdown, no code fences, no explanation.

---
DESIGN SPECIFICATION
---
CSS variables (put in :root):
  --primary:#1a1a2e; --accent:#e94560; --gold:#f5a623;
  --bg:#f4f5f7; --card:#fff; --text:#2c3e50;
  --muted:#7f8c8d; --border:#e2e4e8;

HEADER (dark navy, var(--primary)):
- "The Daily Finance Brief" in white, bold
- Date subtitle below
- Ticker row: scrolling marquee with real/estimated values for NIFTY | SENSEX | S&P 500 | NASDAQ | BTC/USD | ETH/USD | INR/USD | BRENT CRUDE

PERSONALIZATION BAR (id="pbar", hidden by default, shown when user liked items):
- Shows "Personalized for you:" label + top 6 liked tags as gold pill buttons
- "Clear" link to reset

STICKY NAV (7 tabs):
Overview | Companies | Indian Economy | Stock Markets | Sectors | World & Geo | Insights

MAIN CONTENT: max-width 860px, centered, padding 0 16px

---
TAB: Overview
- 4 stat cards: total stories count | critical events count | INR/USD rate | Brent crude price
- Top 3 most important stories as full news cards
- "Connecting the Dots" section (dark gradient bg #1a1a2e, white text):
  Format each chain as: "① [Cause] → [Effect on markets/economy/daily life of Indians]"
  Include 3-5 chains drawn from today's actual articles.
  Tag each: [Inflation ↑/↓] [Markets ↑/↓] [Economy] [Daily Life]

---
TAB: Companies
- Indian company earnings, deals, management changes, product launches
- Use HIGH/MEDIUM criticality mostly

---
TAB: Indian Economy
- RBI policy, rupee movement, inflation, GDP, FPI flows, government fiscal/tax
- CRITICAL label for: rate decisions, budget changes, tax changes

---
TAB: Stock Markets
3 sub-tabs:
  NSE/BSE → Nifty/Sensex summary, top 3 gainers, top 3 losers
  US Markets → S&P 500, Nasdaq, Dow Jones summary
  Crypto → Bitcoin, Ethereum, key altcoin news

---
TAB: Sectors
- Pick 2-3 most newsworthy from: Banking, IT, Pharma, Auto, Energy, FMCG, Realty
- Group cards by sector with a sector header badge

---
TAB: World & Geo
- Global central bank decisions, trade war news, geopolitical events impacting India

---
TAB: Insights
- 1-2 short educational explainers (150-200 words each) tied to TODAY's actual news
- Example: if RBI is in the news, explain what repo rate means and why it matters

---
NEWS CARD STRUCTURE (each card):
  <div class="card" id="card_N">
    <div class="card-meta">
      <span class="source-badge">SOURCE NAME</span>
      <span class="badge critical|high|medium">CRITICAL|HIGH|MEDIUM</span>
      <span class="category">Category</span>
    </div>
    <h3><a href="REAL_URL_HERE" target="_blank" rel="noopener">Headline</a></h3>
    <p>Body text 30-120 words depending on criticality</p>
    <div class="tags">
      <span class="tag">Tag1</span><span class="tag">Tag2</span>
    </div>
    <button class="like-btn" onclick="like('card_N',['Tag1','Tag2'],this)">♡ Like</button>
  </div>

CRITICALITY COLORS:
  .badge.critical {{ background:#e94560; color:#fff }}
  .badge.high     {{ background:#f5a623; color:#fff }}
  .badge.medium   {{ background:#27ae60; color:#fff }}

---
JAVASCRIPT (inline in <script> tag at bottom of <body>):

const TAGS_KEY = 'dfb_tags_v1';
const CARDS_KEY = 'dfb_cards_v1';

function like(id, tags, btn) {{
  let liked = JSON.parse(localStorage.getItem(CARDS_KEY) || '{{}}');
  let counts = JSON.parse(localStorage.getItem(TAGS_KEY) || '{{}}');
  if (liked[id]) {{
    delete liked[id];
    tags.forEach(t => {{ counts[t] = Math.max(0, (counts[t]||0)-1); }});
    btn.textContent = '♡ Like';
    btn.style.background = '';
    btn.style.color = '';
    document.getElementById(id).style.borderLeft = '';
  }} else {{
    liked[id] = tags;
    tags.forEach(t => {{ counts[t] = (counts[t]||0)+1; }});
    btn.textContent = '♥ Liked';
    btn.style.background = 'var(--gold)';
    btn.style.color = '#fff';
    document.getElementById(id).style.borderLeft = '4px solid var(--gold)';
  }}
  localStorage.setItem(CARDS_KEY, JSON.stringify(liked));
  localStorage.setItem(TAGS_KEY, JSON.stringify(counts));
  updatePbar();
}}

function updatePbar() {{
  const counts = JSON.parse(localStorage.getItem(TAGS_KEY) || '{{}}');
  const pbar = document.getElementById('pbar');
  const top = Object.entries(counts).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,6);
  if (!top.length) {{ pbar.style.display='none'; return; }}
  pbar.style.display='block';
  document.getElementById('ptags').innerHTML = top.map(([t])=>
    `<span class="ptag">${{t}}</span>`).join('');
}}

function clearPrefs() {{
  localStorage.removeItem(TAGS_KEY);
  localStorage.removeItem(CARDS_KEY);
  updatePbar();
  document.querySelectorAll('.like-btn').forEach(b=>{{
    b.textContent='♡ Like'; b.style.background=''; b.style.color='';
  }});
  document.querySelectorAll('.card').forEach(c=>{{ c.style.borderLeft=''; }});
}}

function markPersonalized() {{
  const liked = JSON.parse(localStorage.getItem(CARDS_KEY) || '{{}}');
  const counts = JSON.parse(localStorage.getItem(TAGS_KEY) || '{{}}');
  document.querySelectorAll('.card').forEach(card => {{
    const btn = card.querySelector('.like-btn');
    if (liked[card.id]) {{
      card.style.borderLeft = '4px solid var(--gold)';
      if(btn){{ btn.textContent='♥ Liked'; btn.style.background='var(--gold)'; btn.style.color='#fff'; }}
    }}
    const tags = card.querySelectorAll('.tag');
    tags.forEach(t => {{
      if ((counts[t.textContent]||0) > 0) card.style.borderLeft = '4px solid var(--gold)';
    }});
  }});
}}

function showSec(id) {{
  document.querySelectorAll('.section').forEach(s=>s.style.display='none');
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).style.display='block';
  document.querySelector(`[data-sec="${{id}}"]`).classList.add('active');
  if(id==='markets') showSub('nse');
}}

function showSub(id) {{
  document.querySelectorAll('.sub-section').forEach(s=>s.style.display='none');
  document.querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('sub_'+id).style.display='block';
  document.querySelector(`[data-sub="${{id}}"]`).classList.add('active');
}}

window.onload = function() {{
  showSec('overview');
  markPersonalized();
  updatePbar();
}};

---
FOOTER:
List all actual source names used, separated by · (middle dot)

---
TARGET: 15-20 news cards total spread across all tabs.
Always use REAL article URLs from the provided articles as the href for headlines.
Prioritize genuine financial significance. Write body text in clear English.

Now output the complete HTML page:"""

    print("Calling Anthropic API (claude-sonnet-4-6)...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = response.content[0].text.strip()

    # Strip markdown code fences if present
    if html.startswith("```html"):
        html = html[7:]
    elif html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    html = html.strip()

    if not (html.startswith("<!DOCTYPE") or html.startswith("<html")):
        print("ERROR: Response does not look like HTML.")
        print(html[:500])
        sys.exit(1)

    return html


def main():
    today = datetime.now().strftime("%B %d, %Y")
    print(f"=== Daily Finance Brief Generator ===")
    print(f"Date: {today}")
    print()

    # --- Fetch all feeds ---
    print("Fetching RSS feeds...")
    all_articles = []
    for feed_info in RSS_FEEDS:
        arts = fetch_feed(feed_info)
        all_articles.extend(arts)
        print(f"  {feed_info['source']}: {len(arts)} articles")
        time.sleep(0.3)

    if not all_articles:
        print("ERROR: No articles fetched. Check network or feed URLs.")
        sys.exit(1)

    # Deduplicate by title
    seen = set()
    unique = []
    for art in all_articles:
        key = art["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(art)

    print(f"\nTotal unique articles: {len(unique)}")

    # Limit to 80 most recent for token budget
    articles_to_use = unique[:80]
    articles_block = build_articles_block(articles_to_use)

    # --- Generate HTML ---
    html = generate_html(articles_block, today)
    print(f"HTML generated: {len(html):,} bytes")

    # --- Write to index.html ---
    output_path = "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {output_path}")
    print("Done!")


if __name__ == "__main__":
    main()
