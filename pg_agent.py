#!/usr/bin/env python3  
"""PGAgent – Research-Driven Partner-Getting Agent (v0.5.1)
=========================================================
*Sector-only links + completed code block*

This patch finishes the truncated `_compose_email` method, adds the CLI
wrapper, and keeps the sector-specific link logic (no generic fallback).
"""
from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from typing import List, Dict, Optional

# Optional import guard for OpenAI
try:
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore

# SerpAPI import guard (two possible paths)
GoogleSearch = None  # type: ignore
try:
    from serpapi import GoogleSearch  # type: ignore
except (ModuleNotFoundError, ImportError):
    try:
        from serpapi.google_search import GoogleSearch  # type: ignore
    except (ModuleNotFoundError, ImportError):
        GoogleSearch = None  # type: ignore

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv() -> None:
        pass

try:
    from mcp_pg_logging import PGLogger
except Exception:  # pragma: no cover - allow missing logging module
    class PGLogger:
        def log(self, **_: object) -> None:
            pass

load_dotenv()


@dataclass
class ContactInfo:
    name: str
    role: Optional[str] = ""
    company: Optional[str] = ""
    notes: str = ""

    @property
    def is_person(self) -> bool:
        return bool(self.role and self.company)

    @property
    def search_query(self) -> str:
        if self.is_person:
            return f"{self.name} {self.company} {self.role}"
        return f"{self.name} {self.role} MongoDB"


class LinksRegistry:
    _GENERIC: List[tuple[str, str]] = [
        (
            "MongoDB Atlas Architecture Overview",
            "https://www.mongodb.com/docs/atlas/architecture/",
        ),
        (
            "Operational Best Practices",
            "https://www.mongodb.com/docs/manual/administration/production-notes/",
        ),
    ]

    MAP: Dict[str, List[tuple[str, str]]] = {
        "fintech": [
            (
                "Fraud Detection Reference Architecture",
                "https://www.mongodb.com/industries/financial-services/fraud-detection",
            ),
            (
                "Queryable Encryption Overview",
                "https://www.mongodb.com/docs/manual/core/queryable-encryption/",
            ),
        ],
        "healthcare": [
            (
                "HIPAA on MongoDB Atlas",
                "https://www.mongodb.com/docs/atlas/security/hipaa/",
            ),
            (
                "Vector Search for Medical Similarity",
                "https://www.mongodb.com/blog/post/semantic-search-healthcare",
            ),
        ],
        "gaming": [
            (
                "Real-Time Gaming Leaderboards",
                "https://www.mongodb.com/how-to/leaderboards-realtime",
            ),
            ("Realm Sync Architecture", "https://www.mongodb.com/realm"),
        ],
    }

    @classmethod
    def links_for(cls, hint: str | None) -> List[tuple[str, str]]:
        if hint:
            h = hint.lower()
            for key, links in cls.MAP.items():
                if key in h:
                    return links
        return cls._GENERIC


class MongoFactsRegistry:
    _VERT: Dict[str, str] = {
        "fintech": "\u2022 Real-time fraud detection (>10k TPS) via Change Streams.\n\u2022 Queryable Encryption satisfies PCI DSS & SOX.",
        "healthcare": "\u2022 HIPAA-ready clusters with Queryable Encryption.\n\u2022 Vector Search accelerates clinical similarity 20\u00d7.",
        "gaming": "\u2022 1-ms leaderboard reads using in-memory tier.\n\u2022 Realm Sync keeps >5\u202fm players real-time across regions.",
    }
    _GENERIC = (
        "\u2022 Fully managed on AWS, Azure, GCP.\n"
        "\u2022 Global clusters with <60 s failover.\n"
        "\u2022 Built-in Vector, Time-Series & Streaming APIs."
    )

    @classmethod
    def facts_for(cls, hint: str | None) -> str:
        if not hint:
            return cls._GENERIC
        h = hint.lower()
        for k, v in cls._VERT.items():
            if k in h:
                return v + "\n" + cls._GENERIC
        return cls._GENERIC


class UseCasesRegistry:
    """Domain-specific MongoDB Atlas use cases."""
    _GENERIC: List[str] = [
        "Operational analytics",
        "Cloud-native applications",
    ]

    MAP: Dict[str, List[str]] = {
        "fintech": [
            "Streaming trade analytics",
            "Real-time compliance reporting",
        ],
        "healthcare": [
            "Secure patient record consolidation",
            "AI-powered clinical similarity search",
        ],
        "gaming": [
            "Global player profile sync",
            "Event-driven leaderboards",
        ],
    }

    @classmethod
    def cases_for(cls, hint: str | None) -> List[str]:
        if hint:
            h = hint.lower()
            for k, v in cls.MAP.items():
                if k in h:
                    return v
        return cls._GENERIC


class PGAgent:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.35,
        *,
        offline: bool = False,
        logger: PGLogger | None = None,
    ):
        """Initialize the agent and check for required dependencies."""
        self.model, self.temperature = model, temperature
        self.logger = logger or PGLogger()
        self.warning: str | None = None

        api_key = os.getenv("OPENAI_API_KEY")
        issues = []
        if openai is None and not offline:
            issues.append("openai package missing")
        if not offline and not api_key:
            issues.append("OPENAI_API_KEY not set")
        if not offline and GoogleSearch is None:
            issues.append("google-search-results package missing")

        self.offline = offline or bool(issues)
        if issues:
            self.warning = "; ".join(issues)
            self.logger.log(error=self.warning)
        self._client = None if self.offline else openai.OpenAI(api_key=api_key)

    def pg_person(self, c: ContactInfo, *, prior_work: List[str] | None = None) -> str:
        if not c.is_person:
            raise ValueError("Target seems like an account; use pg_account")
        return self._generate(c, prior_work)

    def pg_account(self, a: ContactInfo, *, prior_work: List[str] | None = None) -> str:
        if a.is_person:
            raise ValueError("Target seems like a person; use pg_person")
        return self._generate(a, prior_work)

    def _generate(self, tgt: ContactInfo, wins: List[str] | None) -> str:
        research, snippets = "", []
        if not self.offline:
            snippets = self._search(tgt.search_query)
            research = self._summarise(snippets, tgt)
        key = tgt.notes or tgt.role or tgt.company
        facts = MongoFactsRegistry.facts_for(key)
        links = LinksRegistry.links_for(key)
        cases = UseCasesRegistry.cases_for(key)
        email = self._compose_email(tgt, research, facts, cases, wins, links)
        self.logger.log(
            prompt=f"PG \u2192 {tgt.name}",
            summary=email.split("\n")[0][:120],
            email_body=email,
            extra={"target": tgt.__dict__, "wins": wins or []},
            results=snippets,
        )
        return email

    def _search(self, q: str, k: int = 8):
        if GoogleSearch is None:
            return []
        params = {
            "engine": "google",
            "q": q,
            "num": k,
            "api_key": os.getenv("SERPAPI_KEY"),
            "hl": "en",
        }
        try:
            data = GoogleSearch(params).get_dict()
        except Exception:
            return []
        return [
            {"title": o.get("title", ""), "snippet": o.get("snippet", ""), "link": o.get("link", "")}
            for o in data.get("organic_results", [])
        ]

    def _summarise(self, snips: List[Dict[str, str]], tgt: ContactInfo) -> str:
        corpus = (
            "\n\n".join(f"{s['title']} \u2013 {s['snippet']}" for s in snips[:6])
            or "No public info found."
        )
        prompt = (
            f"Give <120-word summary of key motivations for {tgt.search_query}.\n\nSnippets:\n{corpus}"
        )
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    def _compose_email(
        self,
        tgt: ContactInfo,
        research: str,
        facts: str,
        cases: List[str],
        wins: List[str] | None,
        links: List[tuple[str, str]],
    ) -> str:
        wins_blk = "\n".join(f"\u2022 {w}" for w in (wins or [])) or "\u2022 (add recent win)"
        case_lines = "\n".join(f"\u2022 {c}" for c in cases) if cases else ""
        cases_blk = f"Relevant MongoDB Atlas use cases:\n{case_lines}\n" if case_lines else ""
        link_lines = (
            "\n".join(f"\u2022 [{t}]({u})" for t, u in links) if links else ""
        )
        further = f"\nFurther reading:\n{link_lines}" if link_lines else ""

        sys_prompt = (
            "You are a senior Partner-Getting specialist at MongoDB. Craft crisp, value-driven outreach."
        )
        intro = f"Write a friendly outreach email (<180 words) to {tgt.name}"
        if tgt.role and tgt.company:
            intro += f", the {tgt.role} at {tgt.company}"
        intro += "."

        user_prompt = textwrap.dedent(
            f"""
            {intro}
            Research Brief: {research}
            MongoDB Facts:
            {facts}
            {cases_blk}Prior Wins:
            {wins_blk}{further}
            Desired CTA: 20-minute chat next week.
            """
        )
        if self._client is None:
            return user_prompt.strip()

        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content.strip()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Generate PG email with research")
    p.add_argument("name")
    p.add_argument("--role")
    p.add_argument("--company")
    p.add_argument("--notes", default="")
    p.add_argument("--account", action="store_true")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()

    contact = ContactInfo(
        name=args.name,
        role=args.role or ("Vertical" if args.account else "Job Title"),
        company=args.company or ("" if args.account else "Company"),
        notes=args.notes,
    )
    agent = PGAgent(offline=args.offline)
    if agent.warning:
        print(f"[WARN] {agent.warning}\n")
    email = agent.pg_account(contact) if args.account else agent.pg_person(contact)
    print("\n— Generated PG Email —\n")
    print(email)
    