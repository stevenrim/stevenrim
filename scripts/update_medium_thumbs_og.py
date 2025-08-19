import os, re, html, pathlib, time
import feedparser, requests
from datetime import datetime

FEED_URL = os.getenv("FEED_URL", "https://medium.com/feed/@stevenrim")
README   = pathlib.Path("README.md")

START_RE = r"<!--\s*MEDIUM-OG:START\s*-->"
END_RE   = r"<!--\s*MEDIUM-OG:END\s*-->"

FALLBACK_IMG = "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
}

def fetch_bytes(url, attempts=3, timeout=12):
    last_err = None
    for i in range(1, attempts+1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r.content
        except Exception as e:
            last_err = e
            wait = 1.5 * i
            print(f"[feed] attempt {i} failed: {e}; retrying in {wait:.1f}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch feed after {attempts} attempts: {last_err}")

def parse_feed(url):
    data = fetch_bytes(url)
    d = feedparser.parse(data)
    print(f"[feed] entries parsed: {len(d.entries)}")
    return d

def extract_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            dt = datetime(*entry[key][:6])
            return dt.strftime("%Y-%m-%d")
    return ""

def fetch_og_image(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        t = r.text
        for key in ("og:image:secure_url", "og:image", "twitter:image"):
            m = re.search(
                rf'<meta\b[^>]*?(?:property|name)\s*=\s*["\']{re.escape(key)}["\'][^>]*?content\s*=\s*["\']([^"\']+)["\']',
                t, re.IGNORECASE
            )
            if m:
                return m.group(1)
    except Exception as e:
        print(f"[og] fetch failed for {url}: {e}")
    return None

def first_img_from_html(html_blob):
    if not html_blob:
        return None
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_blob, re.IGNORECASE)
    return m.group(1) if m else None

def build_table(entries, max_items=10, thumb_width=120):
    rows, total, og_hits, fallbacks = [], 0, 0, 0
    for e in entries[:max_items]:
        total += 1
        title = html.escape(e.title or "Untitled")
        link  = e.link
        date  = extract_date(e)

        img = fetch_og_image(link)
        if not img:
            html_blob = e.content[0].value if e.get("content") else e.get("summary", "")
            img = first_img_from_html(html_blob)

        if not img:
            img = FALLBACK_IMG
            fallbacks += 1
        else:
            og_hits += 1

        rows.append(f"""
<tr>
  <td><a href="{link}"><img src="{img}" alt="{title}" width="{thumb_width}"></a></td>
  <td><a href="{link}"><strong>{title}</strong></a><br/><sub>{date}</sub></td>
</tr>""".strip())

    print(f"[stats] total={total}, og_images={og_hits}, fallbacks={fallbacks}")
    return "<table>\n" + "\n".join(rows) + "\n</table>" if rows else "<p>(No items)</p>"

def replace_between_markers(text, start_re, end_re, replacement):
    pattern = re.compile(f"({start_re})(.*)({end_re})", re.DOTALL | re.IGNORECASE)
    if not re.search(pattern, text):
        raise SystemExit("ERROR: README markers not found or mismatched.")
    return re.sub(pattern, rf"\1\n{replacement}\n\3", text)

def main():
    d = parse_feed(FEED_URL)
    if not d.entries:
        raise SystemExit("ERROR: No entries parsed from feed (blocked or empty).")

    block = build_table(d.entries, max_items=10, thumb_width=120)

    md = README.read_text(encoding="utf-8")
    new_md = replace_between_markers(md, START_RE, END_RE, block)
    if new_md != md:
        README.write_text(new_md, encoding="utf-8")
        print("README updated ✅")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
