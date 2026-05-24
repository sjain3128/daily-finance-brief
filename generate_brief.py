#!/usr/bin/env python3
"""
Daily Finance Brief Generator — Compact Edition
Headline + 2 lines per story. Fast, cheap, scannable.
Runs daily via GitHub Actions at 9 AM IST.
"""

import os
import sys
import re
import time
import feedparser
from datetime import datetime, timedelta
import anthropic

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
    {"url": "https://www.thehindu.com/business/Economy/?service=rss",                   "source": "The Hindu Business"},
    {"url": "https://www.businesstoday.in/rssfeeds/1260968891.cms",                      "source": "Business Today"},
]


def fetch_feed(feed_info):
    try:
        feed = feedparser.parse(
            feed_info["url"],
            request_headers={"User-Agent": "DailyFinanceBriefBot/2.0"}
        )
        articles = []
        for entry in feed.entries[:10]:
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            summary = re.sub(r"<[^>]+>", " ", summary)
            summary = re.sub(r"\s+", " ", summary).strip()[:250]
            link    = entry.get("link", "")
            pub     = entry.get("published", entry.get("updated", ""))
            if title and link:
                articles.append({
                    "title": title, "summary": summary,
                    "link": link, "published": pub, "source": feed_info["source"],
                })
        return articles
    except Exception as exc:
        print(f"  WARN: {feed_info['source']}: {exc}")
        return []


def build_articles_block(articles):
    lines = []
    for i, art in enumerate(articles, 1):
        lines.append(f"[{i}] {art['source']} | {art['title']}")
        if art["summary"]:
            lines.append(f"    {art['summary']}")
        lines.append(f"    URL: {art['link']}")
        lines.append("")
    return "\n".join(lines)


def generate_html(articles_block, today):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Generate "The Daily Finance Brief" for {today} as a complete self-contained HTML page.
Output ONLY raw HTML starting with <!DOCTYPE html>. No markdown, no code fences.

NEWS ARTICLES (use these as your source):
{articles_block}

--- DESIGN ---
CSS :root variables:
  --primary:#1a1a2e; --accent:#e94560; --gold:#f5a623;
  --bg:#f4f5f7; --card:#fff; --text:#2c3e50; --muted:#7f8c8d; --border:#e2e4e8;

HEADER: Dark navy (--primary), white text, "The Daily Finance Brief", date below it.
Ticker row: NIFTY | SENSEX | S&P500 | NASDAQ | BTC | INR/USD | BRENT (use values from articles or reasonable estimates)

PERSONALIZATION BAR (id="pbar", hidden by default):
Shows top liked tags as gold pills. "Clear" link.

STICKY NAV — 7 tabs:
Overview | Companies | Indian Economy | Stock Markets | Sectors | World & Geo | Insights

--- COMPACT CARD FORMAT (IMPORTANT) ---
Each news card must be SHORT. Exactly this structure:
  <div class="card" id="card_N">
    <div class="card-meta">
      <span class="src">SOURCE</span>
      <span class="badge critical|high|medium">CRITICAL|HIGH|MEDIUM</span>
    </div>
    <h3><a href="REAL_URL" target="_blank" rel="noopener">Short punchy headline</a></h3>
    <p class="snippet">Two lines max — the single most important fact and its impact. Keep it under 35 words.</p>
    <div class="tags"><span class="tag">Tag1</span><span class="tag">Tag2</span></div>
    <button class="like-btn" onclick="like('card_N',['Tag1','Tag2'],this)">&#9825; Like</button>
  </div>

Badge colors: critical=red (#e94560), high=orange (#f5a623), medium=green (#27ae60). All white text.
Cards have white bg, border-radius 8px, subtle box-shadow, padding 14px 16px, margin-bottom 10px.

--- TABS ---
Overview: 3 stat cards (total stories | critical count | INR/USD) + top 5 most important cards +
  "Connecting the Dots" dark section (bg #1a1a2e, white text):
  3 chains: "① [Event] -> [Effect on Indians / markets / daily life]"
  Each tagged: [Inflation] [Markets] [Economy] [Daily Life]

Companies: company earnings, deals, launches
Indian Economy: RBI, rupee, inflation, GDP, government policy
Stock Markets: 3 sub-tabs (NSE/BSE | US Markets | Crypto)
Sectors: 2-3 top sectors grouped with a header badge
World & Geo: global events impacting India
Insights: 1 short explainer (max 80 words) tied to today's top story

--- JAVASCRIPT (inline in script tag) ---
const TK='dfb_tags_v1', CK='dfb_cards_v1';
function like(id,tags,btn){{
  let l=JSON.parse(localStorage.getItem(CK)||'{{}}'),c=JSON.parse(localStorage.getItem(TK)||'{{}}');
  if(l[id]){{delete l[id];tags.forEach(t=>{{c[t]=Math.max(0,(c[t]||0)-1)}});btn.innerHTML='&#9825; Like';btn.style.cssText='';document.getElementById(id).style.borderLeft='';}}
  else{{l[id]=tags;tags.forEach(t=>{{c[t]=(c[t]||0)+1}});btn.innerHTML='&#9829; Liked';btn.style.cssText='background:var(--gold);color:#fff';document.getElementById(id).style.borderLeft='4px solid var(--gold)';}}
  localStorage.setItem(CK,JSON.stringify(l));localStorage.setItem(TK,JSON.stringify(c));updatePbar();
}}
function updatePbar(){{
  const c=JSON.parse(localStorage.getItem(TK)||'{{}}'),p=document.getElementById('pbar');
  const top=Object.entries(c).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,6);
  if(!top.length){{p.style.display='none';return;}}
  p.style.display='block';
  document.getElementById('ptags').innerHTML=top.map(([t])=>`<span class="ptag">${{t}}</span>`).join('');
}}
function clearPrefs(){{
  localStorage.removeItem(TK);localStorage.removeItem(CK);updatePbar();
  document.querySelectorAll('.like-btn').forEach(b=>{{b.innerHTML='&#9825; Like';b.style.cssText='';}});
  document.querySelectorAll('.card').forEach(c=>{{c.style.borderLeft='';}});
}}
function markPersonalized(){{
  const l=JSON.parse(localStorage.getItem(CK)||'{{}}'),c=JSON.parse(localStorage.getItem(TK)||'{{}}');
  document.querySelectorAll('.card').forEach(card=>{{
    const btn=card.querySelector('.like-btn');
    if(l[card.id]){{card.style.borderLeft='4px solid var(--gold)';if(btn){{btn.innerHTML='&#9829; Liked';btn.style.cssText='background:var(--gold);color:#fff';}}}}
    card.querySelectorAll('.tag').forEach(t=>{{if((c[t.textContent]||0)>0)card.style.borderLeft='4px solid var(--gold)';}});
  }});
}}
function showSec(id){{
  document.querySelectorAll('.section').forEach(s=>s.style.display='none');
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).style.display='block';
  document.querySelector('[data-sec="'+id+'"]').classList.add('active');
  if(id==='markets')showSub('nse');
}}
function showSub(id){{
  document.querySelectorAll('.sub-section').forEach(s=>s.style.display='none');
  document.querySelectorAll('.sub-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('sub_'+id).style.display='block';
  document.querySelector('[data-sub="'+id+'"]').classList.add('active');
}}
window.onload=function(){{showSec('overview');markPersonalized();updatePbar();}};

--- FOOTER ---
Sources: list all source names used, separated by middot

--- RULES ---
- 18-22 cards total across all tabs
- Each card body: MAX 35 words — just the key fact and why it matters
- Use REAL URLs from the articles provided
- Output ONLY the HTML, nothing else"""

    print("Calling Anthropic API...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = response.content[0].text.strip()
    if html.startswith("```html"): html = html[7:]
    elif html.startswith("```"): html = html[3:]
    if html.endswith("```"): html = html[:-3]
    html = html.strip()

    if not (html.startswith("<!DOCTYPE") or html.startswith("<html")):
        print("ERROR: Response is not valid HTML")
        print(html[:300])
        sys.exit(1)

    return html


def main():
    today = datetime.now().strftime("%B %d, %Y")
    print(f"=== Daily Finance Brief ({today}) ===")

    print("Fetching RSS feeds...")
    all_articles = []
    for feed_info in RSS_FEEDS:
        arts = fetch_feed(feed_info)
        all_articles.extend(arts)
        print(f"  {feed_info['source']}: {len(arts)} articles")
        time.sleep(0.3)

    if not all_articles:
        print("ERROR: No articles fetched.")
        sys.exit(1)

    # Deduplicate
    seen, unique = set(), []
    for art in all_articles:
        key = art["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(art)

    print(f"Total unique articles: {len(unique)}")

    articles_block = build_articles_block(unique[:50])
    html = generate_html(articles_block, today)
    print(f"HTML generated: {len(html):,} bytes")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Written to index.html — Done!")


if __name__ == "__main__":
    main()
