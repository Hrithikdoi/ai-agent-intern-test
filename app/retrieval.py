from dataclasses import dataclass
from pathlib import Path
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


KB_DIR = Path(__file__).resolve().parent.parent / "knowledge-base"


@dataclass
class DocumentChunk:
    filename: str
    heading: str
    content: str
    status: str
    audience: str
    policy_authority: str
    effective_date: str


def parse_frontmatter(text: str) -> dict:
    """Extract simple YAML-style metadata from document frontmatter."""
    metadata = {}

    if not text.startswith("---"):
        return metadata

    parts = text.split("---", 2)

    if len(parts) < 3:
        return metadata

    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    return metadata


def parse_document(path: Path) -> list[DocumentChunk]:
    """Split a Markdown document into heading-based chunks."""
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    metadata = parse_frontmatter(text)

    if text.startswith("---"):
        body = text.split("---", 2)[-1]
    else:
        body = text

    sections = re.split(
        r"(?=^#{1,6}\s+)",
        body,
        flags=re.MULTILINE,
    )

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        heading_match = re.match(
            r"^(#{1,6})\s+(.+)",
            section,
        )

        if heading_match:
            heading = heading_match.group(2).strip()
            content = section
        else:
            heading = metadata.get(
                "title",
                path.stem,
            )
            content = section

        chunks.append(
            DocumentChunk(
                filename=path.name,
                heading=heading,
                content=content,
                status=metadata.get(
                    "status",
                    "unknown",
                ),
                audience=metadata.get(
                    "audience",
                    "unknown",
                ),
                policy_authority=metadata.get(
                    "policy_authority",
                    "unknown",
                ),
                effective_date=metadata.get(
                    "effective_date",
                    "",
                ),
            )
        )

    return chunks


def load_knowledge_base() -> list[DocumentChunk]:
    """Load all Markdown documents from the knowledge base."""
    chunks = []

    for path in sorted(KB_DIR.glob("*.md")):
        chunks.extend(parse_document(path))

    return chunks


class Retriever:
    def __init__(self):
        self.chunks = load_knowledge_base()

        if not self.chunks:
            raise ValueError("Knowledge base is empty.")

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )

        self.matrix = self.vectorizer.fit_transform(
            [chunk.content for chunk in self.chunks]
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        """Return the most relevant knowledge-base chunks."""

        if not query.strip():
            return []

        query_lower = query.lower()

        query_vector = self.vectorizer.transform(
            [query]
        )

        scores = cosine_similarity(
            query_vector,
            self.matrix,
        ).flatten()

        results = []

        for index in range(len(self.chunks)):
            score = float(scores[index])

            if score <= 0:
                continue

            chunk = self.chunks[index]

            # Prefer active/current documents.
            if chunk.status == "active":
                score += 0.15

            # Prefer official policy documents.
            if chunk.policy_authority == "official":
                score += 0.05

            # Explicit TrailPlus questions should strongly prefer
            # the TrailPlus membership policy.
            if "trailplus" in query_lower:
                if (
                    "09-trailplus-membership.md" in chunk.filename
                    or "trailplus" in chunk.content.lower()
                    ):
                    score += 0.60

                    if "01-returns-policy-current.md" in chunk.filename:
                        score -= 0.15

            # Regular/standard customer questions should prefer
            # the standard returns policy over TrailPlus exceptions.
            standard_terms = [
                "regular customer",
                "standard customer",
                "standard plan",
                "ordinary customer",
                "regular",
                "standard",
            ]

            if any(term in query_lower for term in standard_terms):
                if (
                    "standard return window" in chunk.heading.lower()
                    or (
                        "standard plan" in chunk.content.lower()
                        and "30 calendar days" in chunk.content.lower()
                    )
                ):
                    score += 0.40

                if "trailplus" in chunk.content.lower():
                    score -= 0.20

            results.append(
                (chunk, score)
            )

        results.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return results[:top_k]