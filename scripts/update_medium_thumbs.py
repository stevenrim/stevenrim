import re
import html
import pathlib
import feedparser
from datetime import datetime

FEED_URL = "https://medium.com/feed/@stevenrim"
README = pathlib.Path("README.md")
START_MARK = "<!-- MEDIUM-LIST:START -->"
END_MARK = "<!-- MEDIUM-LIST:END -->"

FALLBACK_IMG = "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"

def extract_image(entry):
    # Medium usually puts the first image inside <content:encoded>
    html_blob = ""
    if entry.get("content"):
        html_blob = entry.content[0].value
    elif entry.get("summary"):
        html_blob = entry.summary

    m = re.search(r'<img[^>]+src="([^"]+)"', html_blob or "")
    if m:
        return m.group(1)
    return FALLBACK_IMG

def extract_date(entry):
    if entry.get("published_parsed"):
        dt = datetime(*entry.published_parsed[:6])
        return dt.strftime("%Y-%m-%d")
    return ""

def build_table(entries, max_items=10, thumb_width=120):
    rows = []
    for e in entries[:max_items]:
        title = html.escape(e.title or "Untitled")
        link = e.link
        date = extract_date(e)
        img = extract_image(e)

        row_html = f"""
<tr>
  <td>
    <a href="{link}">
      <img src="{img}" alt="{title}" width="{thumb_width}">
    </a>
  </td>
  <td>
    <a href="{link}"><strong>{title}</strong></a><br/>
    <sub>{date}</sub>
  </td>
</tr>""".strip()
        rows.append(row_html)

    return "<table>\n" + "\n".join(rows) + "\n</table>"

def replace_between_markers(text, start, end, replacement):
    pattern = re.compile(rf"({re.escape(start)})(.*)({re.escape(end)})", re.DOTALL)
    return pattern.sub(rf"\1\n{replacement}\
