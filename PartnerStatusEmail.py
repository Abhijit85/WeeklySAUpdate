#!/usr/bin/env python3
# app.py ─ Streamlit UI for Partner-Status Email
# ---------------------------------------------
import streamlit as st
from dataclasses import dataclass, field
from typing import List
import textwrap, datetime


# ───────────────────────────────────────────────
# 1.  Core data models
# ───────────────────────────────────────────────
@dataclass
class Account:
    name: str
    pg_details: List[str] = field(default_factory=list)
    big_rocks: List[str] = field(default_factory=list)

    def render(self, idx: int) -> str:
        indent = " " * 4
        def bullets(items):
            return "\n".join(f"{indent}• {x}" for x in items) if items else indent + "• –"

        return textwrap.dedent(
            f"""
            Account {idx}: **{self.name or '—'}**
            PG details & goals:
            {bullets(self.pg_details)}

            Big Rocks for the week:
            {bullets(self.big_rocks)}
            """
        ).strip()


class PartnerStatusEmail:
    def __init__(
        self,
        link: str,
        results: List[str],
        activities: List[str],
        to: List[str],
        cc: List[str],
        accounts: List[Account],
    ):
        self.link = link
        self.results = results
        self.activities = activities
        self.to = to
        self.cc = cc
        self.accounts = accounts

    def build_body(self) -> str:
        def bullets(items): return "\n".join(f"• {x}" for x in items) if items else "• –"

        parts = [
            f"Send to: {', '.join(self.to) or '—'}",
            f"CC: {', '.join(self.cc) or '—'}",
            "",
            f"Link to Partner Account Plan: {self.link or '—'}",
            "",
            "Important Results from last week:",
            bullets(self.results),
            "",
            "Strategic Workstreams / PG Focus for this week:",
        ]
        # account blocks
        for i, acct in enumerate(self.accounts, 1):
            parts.append(acct.render(i))

        # NEW: Activities section
        parts += [
            "",
            "Activities:",
            bullets(self.activities),
        ]
        return "\n".join(parts)


# ───────────────────────────────────────────────
# 2.  Streamlit UI
# ───────────────────────────────────────────────
st.set_page_config(page_title="Partner-Status Email Builder", layout="wide")
st.title("📧 Partner-Status Email Builder")

with st.sidebar:
    st.header("Recipients")
    to_list = st.text_area("To (comma-separated)", value="eae@example.com, rd@example.com")
    cc_list = st.text_area("CC (comma-separated)", value="engagement-mgr@example.com")
    link = st.text_input("Link to Partner Account Plan", value="https://example.com/partner-plan")

    st.markdown("---")
    st.header("Important Results (last week)")
    important_raw = st.text_area("One bullet per line", height=100,
                                 placeholder="Closed $xxx ARR\nSourced y new NWLs")

    st.markdown("---")
    n_accounts = st.number_input("How many Accounts this week?",
                                 min_value=1, max_value=10, step=1, value=2)

    st.markdown("---")
    st.header("Activities")
    activities_raw = st.text_area("One activity per line",
                                  height=120,
                                  placeholder="Customer workshop on Friday\nUpdate partner enablement deck")


# ───────────────────────────────────────────────
# 3.  Account editors
# ───────────────────────────────────────────────
accounts_ui: List[Account] = []
st.subheader("Strategic Workstreams / PG Focus")
for idx in range(1, n_accounts + 1):
    with st.expander(f"Account {idx}", expanded=(idx == 1)):
        name = st.text_input(f"Account {idx} Name", key=f"name{idx}")
        pg_raw = st.text_area("PG details & goals (one per line)", key=f"pg{idx}", height=80)
        br_raw = st.text_area("Big Rocks for the week (one per line)", key=f"br{idx}", height=80)

        accounts_ui.append(
            Account(
                name=name.strip(),
                pg_details=[x.strip() for x in pg_raw.splitlines() if x.strip()],
                big_rocks=[x.strip() for x in br_raw.splitlines() if x.strip()],
            )
        )

# ───────────────────────────────────────────────
# 4.  Generate / download
# ───────────────────────────────────────────────
if st.button("🚀 Generate Email", type="primary"):
    email = PartnerStatusEmail(
        link=link.strip(),
        results=[x.strip() for x in important_raw.splitlines() if x.strip()],
        activities=[x.strip() for x in activities_raw.splitlines() if x.strip()],
        to=[x.strip() for x in to_list.split(",") if x.strip()],
        cc=[x.strip() for x in cc_list.split(",") if x.strip()],
        accounts=accounts_ui,
    )
    body = email.build_body()

    st.subheader("📄 Preview")
    st.code(body)

    file_name = f"partner_status_{datetime.date.today()}.txt"
    st.download_button(
        label="💾 Download .txt",
        data=body.encode("utf-8"),
        file_name=file_name,
        mime="text/plain",
    )

    st.success("Email draft generated — copy it or download the .txt!")
