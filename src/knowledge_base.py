"""
knowledge_base.py
------------------
Tool #3 in the agent's toolchain: a small local knowledge base of
space-traffic-management practice, plus a lightweight TF-IDF retriever.

The entries below are written in plain, original language summarizing
widely-known, publicly discussed operational practice in the space traffic
management community (e.g. conjunction risk tiers, typical action
thresholds). They are not verbatim excerpts from any single document.

In a larger system this would be swapped for a real vector store over
actual operator handbooks; the interface (`retrieve`) is designed so that
swap requires no changes to the calling agent code.
"""
from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_ENTRIES = [
    {
        "id": "risk-tiers",
        "text": (
            "Conjunction risk is commonly bucketed into tiers by miss distance and "
            "probability of collision. A rough operational convention: events with a "
            "predicted miss distance under roughly 1 km are treated as high concern "
            "and usually warrant an active maneuver evaluation; events between about "
            "1 and 5 km warrant close monitoring and a maneuver plan on standby; "
            "events beyond 5 to a few tens of km are typically logged and watched "
            "but rarely acted on unless later tracking tightens the estimate."
        ),
    },
    {
        "id": "tracking-uncertainty",
        "text": (
            "Two-line element sets degrade in accuracy the further you propagate from "
            "their epoch, especially for low Earth orbit objects subject to drag. "
            "Predictions more than a few days from epoch, or based on TLEs older than "
            "about a week, should be treated as indicative rather than authoritative, "
            "and re-screened against fresher data before any operational decision."
        ),
    },
    {
        "id": "maneuver-tradeoffs",
        "text": (
            "Collision-avoidance maneuvers are not free: they burn propellant, can "
            "temporarily interrupt a satellite's mission, and if timed incorrectly can "
            "occasionally worsen a conjunction with a different, previously "
            "unscreened object. Operators generally prefer the smallest maneuver that "
            "moves the miss distance safely past the risk threshold, executed as late "
            "as is safely possible so as to use the most up-to-date tracking data."
        ),
    },
    {
        "id": "debris-mitigation",
        "text": (
            "General debris mitigation guidance (echoed by bodies such as the UN "
            "Committee on the Peaceful Uses of Outer Space and national space "
            "agencies) emphasizes minimizing the creation of new debris, deorbiting "
            "defunct hardware within a bounded post-mission lifetime, and passivating "
            "spent stages so they cannot explode from residual energy."
        ),
    },
    {
        "id": "false-positive-context",
        "text": (
            "Coarse conjunction screens that sample distance on a fixed time grid can "
            "miss the true closest approach between samples, or can flag events that "
            "resolve to a larger miss distance once finer sampling or better tracking "
            "is applied. A screening flag should be read as 'worth a closer look,' not "
            "as a confirmed collision prediction."
        ),
    },
    {
        "id": "pc-threshold",
        "text": (
            "When a probability of collision is computed from real tracking-derived "
            "covariance (not an assumed placeholder), the most commonly cited "
            "operational action threshold is around 1 in 10,000 (1e-4): events at or "
            "above that level are typically escalated for an active maneuver "
            "evaluation, events in the 1e-6 to 1e-4 range warrant monitoring, and "
            "events below 1e-6 are usually logged without further action. Individual "
            "operators adjust this based on asset value, maneuver cost, and mission "
            "phase."
        ),
    },
]


@dataclass
class RetrievedNote:
    id: str
    text: str
    score: float


class KnowledgeBase:
    def __init__(self, entries: list[dict] | None = None):
        self.entries = entries or KNOWLEDGE_ENTRIES
        self._texts = [e["text"] for e in self.entries]
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(self._texts)

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedNote]:
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
        return [
            RetrievedNote(id=self.entries[i]["id"], text=self.entries[i]["text"], score=float(sims[i]))
            for i in ranked
        ]
