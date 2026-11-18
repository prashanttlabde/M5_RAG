"""Implements architecture §10 Fee Explainer: bullets, citations, fact-check results, links, Last checked."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import ui
import yaml

from src import config

ui.page_header("Fee Explainer", "Plain-language answer, written only from official pages")
meta = ui.load_json(config.FEE_EXPLAINER_JSON)
if meta is None:
    ui.empty_state("The fee explainer", "Run make rag after filling config/sources.yaml.")
    st.stop()

sources = {}
if config.SOURCES_YAML.exists():
    sources = {s["source_id"]: s for s in (yaml.safe_load(config.SOURCES_YAML.read_text(encoding="utf-8")) or {}).get("sources", [])}
chunks = {}
if config.CHUNKS_JSONL.exists():
    import json
    chunks = {c["chunk_id"]: c for c in map(json.loads, filter(str.strip, config.CHUNKS_JSONL.read_text(encoding="utf-8").splitlines()))}

ok = meta["status"] == "ok"
st.markdown(
    f'Fee issue: <b>{ui.esc(meta["topic"].replace("_", " "))}</b> &nbsp; '
    + (ui.badge("ok", "Verified") if ok else ui.badge("fail", "Needs human review")),
    unsafe_allow_html=True,
)
st.subheader("What the official pages say")
for b in meta["bullets"]:
    text = b["text"]
    with st.container(border=True):
        st.markdown(text)
        chunk = chunks.get(b["chunk_id"])
        if chunk:
            with st.expander("Official text this is based on"):
                st.write(chunk["text"])
                st.caption(f"Chunk {b['chunk_id']}")

st.subheader("Fact-check")
ui.table(
    ["Measure", "Result"],
    [["Bullets that passed validation and the fact-check", len(meta["bullets"])],
     ["Bullets dropped", len(meta["rejected"])], ["Bullets rewritten once", meta["rewritten_count"]]],
)

st.subheader("Official sources")
rows = [[ui.raw(f'<a href="{ui.esc(l["url"])}" target="_blank" rel="noopener">{ui.esc(l["title"])}</a>')] for l in meta["links"]]
ui.table(["Link"], rows)
st.markdown(f"**Last checked:** {ui.esc(meta['last_checked'])}")
if sources:
    with st.expander("All pages this explainer may draw from"):
        for s in sources.values():
            st.markdown(f"- [{s['title']}]({s['url']})")
