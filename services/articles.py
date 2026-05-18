import base64
import html
import mimetypes
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

ARTICLES_DIR = Path(__file__).resolve().parent.parent / "articles"


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    author: str
    published_at: Optional[date]
    status: str
    category: str
    tags: List[str]
    summary: str
    cover_image: str
    featured: bool
    body: str
    path: Path


def _parse_value(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "yes"}:
        return True
    if value.lower() in {"false", "no"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        raw_items = value[1:-1].split(",")
        return [item.strip().strip("\"'") for item in raw_items if item.strip()]
    return value.strip("\"'")


def _parse_front_matter(text: str) -> tuple[Dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: Dict[str, Any] = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = _parse_value(value)

    return meta, parts[2].lstrip()


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_tags(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _article_from_file(path: Path) -> Article:
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    slug = str(meta.get("slug") or path.stem)

    return Article(
        slug=slug,
        title=str(meta.get("title") or path.stem.replace("-", " ").title()),
        author=str(meta.get("author") or "The Big Whammy"),
        published_at=_parse_date(meta.get("date")),
        status=str(meta.get("status") or "draft").lower(),
        category=str(meta.get("category") or "Announcements"),
        tags=_parse_tags(meta.get("tags")),
        summary=str(meta.get("summary") or ""),
        cover_image=str(meta.get("cover_image") or ""),
        featured=bool(meta.get("featured") or False),
        body=body,
        path=path,
    )


@st.cache_data(ttl=60, show_spinner=False)
def load_articles(include_drafts: bool = False) -> List[Article]:
    if not ARTICLES_DIR.exists():
        return []

    articles: List[Article] = []
    for path in sorted(ARTICLES_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        article = _article_from_file(path)
        if include_drafts or article.status == "published":
            articles.append(article)

    return sorted(
        articles,
        key=lambda item: (
            item.featured,
            item.published_at or date.min,
            item.title.lower(),
        ),
        reverse=True,
    )


def find_article(slug: str, include_drafts: bool = False) -> Optional[Article]:
    for article in load_articles(include_drafts=include_drafts):
        if article.slug == slug:
            return article
    return None


def article_url(slug: str) -> str:
    return f"/Articles?slug={slug}"


def format_article_date(article: Article) -> str:
    if not article.published_at:
        return "Undated"
    return article.published_at.strftime("%d %b %Y")


def resolve_article_asset(article: Article, asset_path: str) -> Optional[Path]:
    if not asset_path or re.match(r"^https?://", asset_path):
        return None

    path = Path(asset_path)
    candidates = [
        article.path.parent / path,
        ARTICLES_DIR / path,
    ]

    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(ARTICLES_DIR.resolve())
        except ValueError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved

    return None


def render_cover_image(article: Article) -> None:
    if not article.cover_image:
        return
    if re.match(r"^https?://", article.cover_image):
        st.image(article.cover_image, use_container_width=True)
        return

    local_path = resolve_article_asset(article, article.cover_image)
    if local_path:
        st.image(str(local_path), use_container_width=True)


def _image_to_data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_article_body(article: Article) -> None:
    def replace_image(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        image_path = match.group(2).strip()
        if re.match(r"^https?://", image_path):
            return match.group(0)

        local_path = resolve_article_asset(article, image_path)
        if not local_path:
            return match.group(0)

        return (
            f'<img src="{_image_to_data_uri(local_path)}" '
            f'alt="{html.escape(alt_text)}" '
            'style="max-width:100%; height:auto; border-radius:8px;" />'
        )

    body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_image, article.body)
    st.markdown(body, unsafe_allow_html=True)
