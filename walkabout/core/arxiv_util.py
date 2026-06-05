import re
import xml.etree.ElementTree as ET

from walkabout.core.file_util import cached
from walkabout.core.reference import Reference


def canonicalize(text: str):
    """Remove newlines and extra whitespace with one space."""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def is_arxiv_link(url: str) -> bool:
    return url.startswith("https://arxiv.org/")

def arxiv_reference(url: str, **kwargs) -> Reference:
    """
    Parse an arXiv reference from a URL (e.g., https://arxiv.org/abs/2005.14165).
    Cache the result.
    """
    # Figure out the paper ID
    paper_id = None
    m = re.search(r'arxiv.org\/...\/(\d+\.\d+)(v\d)?(\.pdf)?$', url)
    if not m:
        raise ValueError(f"Cannot handle this URL: {url}")
    paper_id = m.group(1)

    metadata_url = f"https://export.arxiv.org/api/query?id_list={paper_id}"
    metadata_path = cached(metadata_url, "arxiv")
    with open(metadata_path, "r", encoding="utf-8") as f:
        contents = f.read()
    root = ET.fromstring(contents)

    # Extract the relevant metadata
    ns = "http://www.w3.org/2005/Atom"
    entry = root.find(f"{{{ns}}}entry")
    if entry is None:
        raise ValueError(f"No entry found in arXiv API response for {paper_id}")

    title_el = entry.find(f"{{{ns}}}title")
    title = canonicalize(title_el.text) if title_el is not None else paper_id

    authors = []
    for author in entry.findall(f"{{{ns}}}author"):
        name_el = author.find(f"{{{ns}}}name")
        if name_el is not None and name_el.text:
            authors.append(canonicalize(name_el.text))

    summary_el = entry.find(f"{{{ns}}}summary")
    summary = canonicalize(summary_el.text) if summary_el is not None else ""

    published_el = entry.find(f"{{{ns}}}published")
    published = published_el.text if published_el is not None else ""

    return Reference(
        title=title,
        authors=authors,
        url=url,
        date=published,
        description=summary,
        **kwargs,
    )
