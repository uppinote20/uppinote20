import feedparser
import pathlib
import re
import os
import datetime
from github import Github

root = pathlib.Path(__file__).parent.resolve()

TOKEN = os.environ.get("GH_TOKEN", "")
TITLE_MAX_LEN = 25
BLOG_RSS = "https://blog.uppinote.dev/rss/"


def replace_chunk(content, marker, chunk):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    chunk = "<!-- {} starts -->\n{}\n<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


def truncate(text, max_len=TITLE_MAX_LEN):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 2] + ".."


def parse_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.datetime(*parsed[:6]).strftime("%Y-%m-%d")
    return ""


def fetch_releases(token):
    g = Github(token)
    user = g.get_user()
    releases = []

    for repo in user.get_repos(type="owner"):
        if repo.fork:
            continue
        try:
            for release in repo.get_releases():
                if release.draft:
                    continue
                title = (release.title or release.tag_name or "").strip()
                releases.append(
                    {
                        "repo": repo.name,
                        "title": title,
                        "url": release.html_url,
                        "date": release.published_at.strftime("%Y-%m-%d"),
                    }
                )
                break  # latest release only per repo
        except Exception:
            continue

    releases.sort(key=lambda r: r["date"], reverse=True)
    return releases[:6]


def fetch_blog():
    entries = feedparser.parse(BLOG_RSS).get("entries", [])
    results = []
    for entry in entries:
        title = truncate(entry.get("title", ""))
        url = entry.get("link", "").split("#")[0]
        date = parse_date(entry)
        if title and url and date:
            results.append({"title": title, "url": url, "date": date})
        if len(results) >= 6:
            break
    return results


if __name__ == "__main__":
    readme = root / "README.md"
    content = readme.read_text()

    releases = fetch_releases(TOKEN)
    releases_md = "<br>\n".join(
        '• [{repo} {title}]({url}) - {date}'.format(**r) for r in releases
    )
    content = replace_chunk(content, "releases", releases_md)

    posts = fetch_blog()
    blog_md = "<br>\n".join(
        '• [{title}]({url}) - {date}'.format(**p) for p in posts
    )
    content = replace_chunk(content, "blog", blog_md)

    readme.write_text(content)
