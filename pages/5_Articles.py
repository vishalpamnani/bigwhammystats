import streamlit as st

from services.articles import (
    article_url,
    find_article,
    format_article_date,
    load_articles,
    render_article_body,
    render_cover_image,
)
from utils import add_logo_fixed

st.set_page_config(page_title="Big Whammy Articles", layout="wide")
add_logo_fixed("TBWlogo.png", width=120, top=20, left=16)

query_slug = st.query_params.get("slug", "")
if isinstance(query_slug, list):
    query_slug = query_slug[0] if query_slug else ""

if query_slug:
    article = find_article(query_slug)
    if not article:
        st.error("Article not found, or it is still in draft.")
        if st.button("Back to articles"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    if st.button("← All articles"):
        st.query_params.clear()
        st.rerun()

    st.title(article.title)
    st.caption(
        f"{format_article_date(article)} · {article.author} · {article.category}"
    )
    if article.tags:
        st.caption("Tags: " + ", ".join(article.tags))

    render_cover_image(article)
    render_article_body(article)
    st.stop()

st.title("📝 Articles")
st.caption("Big Whammy stories, awards, reviews, and announcements.")

articles = load_articles()

if not articles:
    st.info("No published articles yet.")
    st.stop()

featured = [article for article in articles if article.featured]
regular = [article for article in articles if not article.featured]

if featured:
    st.subheader("Featured")
    for article in featured:
        with st.container(border=True):
            st.markdown(f"### [{article.title}]({article_url(article.slug)})")
            st.caption(
                f"{format_article_date(article)} · {article.author} · {article.category}"
            )
            if article.summary:
                st.write(article.summary)

st.subheader("Latest")
for article in regular or articles:
    with st.container(border=True):
        st.markdown(f"### [{article.title}]({article_url(article.slug)})")
        st.caption(
            f"{format_article_date(article)} · {article.author} · {article.category}"
        )
        if article.summary:
            st.write(article.summary)
        if article.tags:
            st.caption("Tags: " + ", ".join(article.tags))
