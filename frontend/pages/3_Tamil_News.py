import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from frontend.services.api import api_client

st.set_page_config(
    page_title="Tamil News Bias & Political Coverage Analyzer - CivicLens TN",
    page_icon="📰",
    layout="wide"
)

st.title("📰 Tamil News Bias & Political Coverage Analyzer")
st.subheader("Multi-Dimensional Coverage Analysis across Tamil & English News Outlets")

# Standardized tab navigation for Phase 4.9 Dashboard
tab_explorer, tab_article, tab_source_comp, tab_event, tab_topics, tab_entities, tab_bias, tab_source_detail = st.tabs([
    "🔍 News Explorer",
    "📄 Article Detail",
    "⚖️ Source Comparison",
    "📍 Event Coverage",
    "📊 Topic Trends",
    "🏛️ Political Entity Coverage",
    "📐 Observed Coverage Indicators",
    "🏢 Source Profile"
])

# Shared helper function to load filters
@st.cache_data(ttl=60)
def load_filter_options():
    ok_src, sources_res = api_client.get_news_sources()
    sources = sources_res if ok_src and isinstance(sources_res, list) else []

    ok_top, topics_res = api_client.get_news_topics()
    topics = topics_res if ok_top and isinstance(topics_res, list) else []

    ok_ent, entities_res = api_client.get_news_entities()
    entities = entities_res if ok_ent and isinstance(entities_res, list) else []

    ok_evt, events_res = api_client.get_news_events()
    events = events_res if ok_evt and isinstance(events_res, list) else []

    return sources, topics, entities, events

sources_list, topics_list, entities_list, events_list = load_filter_options()

source_options = ["All"] + [s["source_id"] for s in sources_list]
topic_options = ["All"] + [t["topic_id"] for t in topics_list]
entity_options = ["All"] + [e["entity_id"] for e in entities_list]
person_options = ["All"] + [e["entity_id"] for e in entities_list if e.get("entity_type") == "person"]
party_options = ["All"] + [e["entity_id"] for e in entities_list if e.get("entity_type") == "party"]
event_options = ["All"] + [ev["event_id"] for ev in events_list]


# =============================================================================
# TAB 1: NEWS EXPLORER
# =============================================================================
with tab_explorer:
    st.markdown("### 🔍 Search & Filter News Articles")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        sel_source = st.selectbox("Source Outlet", source_options, key="exp_src")
        sel_lang = st.selectbox("Language", ["All", "ta", "en"], key="exp_lang")
    with col_f2:
        sel_topic = st.selectbox("Policy Topic", topic_options, key="exp_topic")
        sel_party = st.selectbox("Political Party", party_options, key="exp_party")
    with col_f3:
        sel_person = st.selectbox("Political Person", person_options, key="exp_person")
        sel_event = st.selectbox("Political Event", event_options, key="exp_event")
    with col_f4:
        search_kw = st.text_input("Keyword Search", placeholder="e.g., பட்ஜெட் / Metro", key="exp_search")
        date_range = st.date_input("Date Range", value=(date.today() - timedelta(days=90), date.today()), key="exp_date")

    date_from_str = date_range[0].isoformat() if isinstance(date_range, tuple) and len(date_range) > 0 else None
    date_to_str = date_range[1].isoformat() if isinstance(date_range, tuple) and len(date_range) > 1 else None

    # Fetch filtered articles
    with st.spinner("Fetching articles..."):
        ok_arts, arts_data = api_client.get_news_articles(
            source_id=sel_source,
            language=sel_lang,
            date_from=date_from_str,
            date_to=date_to_str,
            topic_id=sel_topic,
            party_id=sel_party,
            person_id=sel_person,
            event_id=sel_event,
            search=search_kw,
            limit=25
        )

    if ok_arts and isinstance(arts_data, list) and len(arts_data) > 0:
        st.success(f"Found {len(arts_data)} article(s)")
        for art in arts_data:
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"#### [{art['title']}]({art['url']})")
                    meta_str = f"**Source:** `{art['source_id']}` | **Lang:** `{art['language']}` | **Published:** `{art.get('publication_date', 'N/A')[:10] if art.get('publication_date') else 'N/A'}` | **Words:** `{art.get('word_count', 0)}`"
                    st.markdown(meta_str)

                    if art.get("is_test_fixture"):
                        st.info("⚠️ **TEST FIXTURE — NOT REAL NEWS DATA**")
                with c2:
                    if st.button("📄 Detail", key=f"btn_{art['article_id']}"):
                        st.session_state["selected_article_id"] = art["article_id"]
                        st.info(f"Article ID `{art['article_id']}` selected. Click on the **Article Detail** tab above to view full analysis.")
                st.divider()
    else:
        st.warning("No articles matched the specified filters. Try broadening your criteria.")


# =============================================================================
# TAB 2: ARTICLE DETAIL
# =============================================================================
with tab_article:
    st.markdown("### 📄 Article Analysis & Provenance")

    default_art_id = st.session_state.get("selected_article_id", "")
    art_id_input = st.text_input("Enter Article ID to Inspect", value=default_art_id, placeholder="e.g., art_p48_001")

    if art_id_input:
        with st.spinner("Retrieving article detail..."):
            ok_detail, detail_data = api_client.get_news_article_detail(art_id_input)

        if ok_detail and detail_data:
            if detail_data.get("is_test_fixture"):
                st.warning("⚠️ **TEST FIXTURE — NOT REAL NEWS DATA**. This record is a synthetic fixture generated for pipeline validation.")

            st.markdown(f"## {detail_data['title']}")
            st.markdown(f"**Publisher Source:** `{detail_data['source_id']}` | **Author:** {detail_data.get('author', 'Staff Reporter')} | **Language:** `{detail_data['language']}` | **Published:** `{detail_data.get('publication_date', 'N/A')}`")
            st.markdown(f"[🔗 Original Source Link]({detail_data['url']})")

            c_text, c_meta = st.columns([3, 2])
            with c_text:
                st.markdown("### Article Text Content")
                st.text_area("Body Text", value=detail_data["article_text"], height=300, disabled=True)

            with c_meta:
                st.markdown("### Extracted Intelligence")
                
                # Entities
                st.markdown("**Mentioned Entities:**")
                for e in detail_data.get("entities", []):
                    st.markdown(f"- `{e['entity_id']}` (Mentions: {e['mention_count']}, Prominence: {e['prominence_score']})")

                # Topics
                st.markdown("**Policy Topics:**")
                for t in detail_data.get("topics", []):
                    st.markdown(f"- `{t['topic_id']}` (Relevance: {t['relevance_score']})")

                # Linguistic & Framing Signals
                feats = detail_data.get("features") or {}
                st.markdown("**Linguistic & Framing Signals:**")
                st.metric("Headline Sentiment", feats.get("headline_sentiment", 0.0))
                st.metric("Body Sentiment", feats.get("body_sentiment", 0.0))
                st.metric("Quote Count", feats.get("quote_count", 0))
                st.metric("Official Citations", feats.get("official_source_citation_count", 0))

            # Explicit Provenance Block
            st.markdown("---")
            with st.expander("🛡️ Data Provenance & Verification Metadata", expanded=True):
                prov = detail_data.get("provenance", {})
                st.json(prov)
        else:
            st.error(f"Article ID `{art_id_input}` not found.")
    else:
        st.info("Select an article from the **News Explorer** tab or enter an Article ID above.")


# =============================================================================
# TAB 3: SOURCE COMPARISON
# =============================================================================
with tab_source_comp:
    st.markdown("### ⚖️ Side-by-Side News Outlet Comparison")

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        cmp_src_a = st.selectbox("Select Primary Outlet (Source A)", source_options[1:] if len(source_options) > 1 else source_options, key="cmp_sa")
    with col_s2:
        cmp_src_b = st.selectbox("Select Comparison Outlet (Source B)", source_options[2:] if len(source_options) > 2 else source_options, key="cmp_sb")
    with col_s3:
        cmp_days = st.slider("Time Window (Days)", min_value=7, max_value=90, value=30, key="cmp_days")

    if st.button("Run Side-by-Side Comparison", key="btn_run_comp"):
        with st.spinner("Calculating pairwise comparison metrics..."):
            ok_comp, comp_res = api_client.get_news_source_comparison(cmp_src_a, cmp_src_b, days_window=cmp_days)

        if ok_comp and comp_res:
            st.success("Comparison calculated successfully.")
            
            c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5)
            c_m1.metric("Wording Similarity", f"{comp_res.get('wording_similarity_score', 0.0) * 100:.1f}%")
            c_m2.metric("Topic Divergence", comp_res.get("topic_emphasis_divergence", 0.0))
            c_m3.metric("Entity Divergence", comp_res.get("entity_prominence_divergence", 0.0))
            c_m4.metric("Framing Divergence", comp_res.get("framing_divergence", 0.0))
            c_m5.metric("Coverage Disparity", comp_res.get("coverage_difference_score", 0.0))

            norm_comp = comp_res.get("comparison_data", {}).get("normalized_comparisons", {})
            if norm_comp:
                st.markdown("#### Normalized Framing Distribution Comparison")
                df_frame = pd.DataFrame([
                    {"Outlet": cmp_src_a, **norm_comp.get("source_a", {})},
                    {"Outlet": cmp_src_b, **norm_comp.get("source_b", {})}
                ])
                st.dataframe(df_frame, use_container_width=True)

            with st.expander("Methodology & Calculation Version"):
                st.markdown(f"- **Methodology Version:** `{comp_res.get('methodology_version', 'v1.0')}`")
                st.markdown(f"- **Calculation Version:** `{comp_res.get('calculation_version', 'v1.0')}`")
                st.caption("Differences in metrics reflect variations in beat focus, quoting patterns, and topic prioritization. They do not constitute proof of partisan bias.")


# =============================================================================
# TAB 4: EVENT COVERAGE
# =============================================================================
with tab_event:
    st.markdown("### 📍 Ground-Truth Event Coverage Analysis")

    if events_list:
        selected_event_id = st.selectbox("Select Ground-Truth Political Event", [ev["event_id"] for ev in events_list], key="tab_evt_sel")

        with st.spinner("Fetching event coverage breakdown..."):
            ok_evt_det, evt_det = api_client.get_news_event_detail(selected_event_id)

        if ok_evt_det and evt_det:
            st.markdown(f"### Event: {evt_det['event_name']}")
            st.markdown(f"**Date:** `{evt_det.get('event_date', 'N/A')}` | **Location:** `{evt_det.get('location', 'N/A')}`")
            st.markdown(f"**Official Reference:** `{evt_det.get('official_reference', 'N/A')}`")
            st.markdown(f"*{evt_det.get('description', '')}*")

            st.markdown("#### Linked Outlet Coverage Articles")
            linked = evt_det.get("linked_articles", [])
            if linked:
                df_links = pd.DataFrame(linked)
                st.dataframe(df_links, use_container_width=True)
            else:
                st.info("No articles currently linked to this event.")

            cross_summary = evt_det.get("cross_source_summary", {})
            if cross_summary and "source_coverage" in cross_summary:
                st.markdown("#### Cross-Outlet Comparative Summary")
                st.json(cross_summary["source_coverage"])
                
                disparities = cross_summary.get("coverage_disparities", [])
                if disparities:
                    st.markdown("#### Observed Coverage Disparities")
                    for d in disparities:
                        st.warning(f"**{d.get('disparity_type', 'Disparity')}**: {d.get('description')}")
    else:
        st.info("No ground-truth events currently loaded in database.")


# =============================================================================
# TAB 5: TOPIC TRENDS
# =============================================================================
with tab_topics:
    st.markdown("### 📊 Policy Topic Distribution Trends")

    if topics_list:
        df_top = pd.DataFrame(topics_list)
        st.dataframe(df_top[["topic_id", "topic_code", "topic_name", "description", "article_count"]], use_container_width=True)
    else:
        st.info("No topic taxonomy loaded.")


# =============================================================================
# TAB 6: POLITICAL ENTITY COVERAGE
# =============================================================================
with tab_entities:
    st.markdown("### 🏛️ Political Entity Coverage")

    ent_filter_type = st.radio("Entity Category", ["All", "person", "party", "department", "location"], horizontal=True, key="ent_cat")
    with st.spinner("Fetching entity coverage data..."):
        ok_ents, ents_data = api_client.get_news_entities(entity_type=ent_filter_type)

    if ok_ents and ents_data:
        df_ents = pd.DataFrame(ents_data)
        st.dataframe(df_ents, use_container_width=True)
    else:
        st.info("No political entities found matching category.")


# =============================================================================
# TAB 7: OBSERVED COVERAGE INDICATORS (BIAS PAGE)
# =============================================================================
with tab_bias:
    st.markdown("### 📐 Observed Coverage Indicators")

    st.markdown("""
    > [!IMPORTANT]
    > **Methodology Safeguard**: This platform does **NOT** compute or display a scalar "bias score" claiming *"Source X is biased"*. 
    > Instead, it displays 12 independent multi-dimensional coverage indicators measuring reporting patterns, quoting distributions, and topic prioritization.
    """)

    bias_src_sel = st.selectbox("Select News Source", source_options[1:] if len(source_options) > 1 else source_options, key="bias_src_sel")

    if st.button("Calculate Multi-Dimensional Indicators", key="btn_calc_bias"):
        with st.spinner("Computing 12 reproducible indicators..."):
            api_client.calculate_news_indicators(bias_src_sel, days_window=30)

    with st.spinner("Loading observed indicators..."):
        ok_ind, ind_data = api_client.get_news_bias_indicators(source_id=bias_src_sel)

    if ok_ind and ind_data:
        st.success(f"Retrieved {len(ind_data)} indicator measurement(s) for `{bias_src_sel}`")
        for ind in ind_data:
            with st.expander(f"Indicator: {ind['metric_type']} (Confidence: {ind.get('statistical_confidence', 1.0)})", expanded=True):
                st.markdown(f"**Value:** `{ind['indicator_value']}`")
                st.markdown(f"**Interpretation Label:** {ind['interpretation_label']}")
                st.markdown(f"**Explanation:** {ind.get('explanation')}")
                st.markdown(f"**Methodology Version:** `{ind.get('methodology_version', 'v1.0')}` | **Calculation Version:** `{ind.get('calculation_version', 'v1.0')}`")
                if ind.get("metadata_json"):
                    st.json(ind["metadata_json"])
    else:
        st.info(f"No calculated indicators found for `{bias_src_sel}`. Click the button above to calculate indicators.")


# =============================================================================
# TAB 8: SOURCE PROFILE
# =============================================================================
with tab_source_detail:
    st.markdown("### 🏢 News Source Registry Profile")

    profile_src_sel = st.selectbox("Select Outlet Profile", source_options[1:] if len(source_options) > 1 else source_options, key="prof_src_sel")

    matched_src = next((s for s in sources_list if s["source_id"] == profile_src_sel), None)
    if matched_src:
        st.markdown(f"## {matched_src['source_name']}")
        st.markdown(f"**Domain:** [{matched_src['domain']}](https://{matched_src['domain']}) | **Type:** `{matched_src['source_type']}` | **Language:** `{matched_src['language']}` | **Status:** `{matched_src['active_status']}`")

        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.metric("Total Ingested Articles", matched_src.get("article_count", 0))
            st.markdown(f"**Official Portal URL:** [{matched_src.get('official_url', 'N/A')}]({matched_src.get('official_url', '#')})")

        with c_p2:
            st.markdown("**Historical Coverage Metrics:**")
            ok_m, cov_m = api_client.get_news_coverage(source_id=profile_src_sel)
            if ok_m and cov_m:
                st.json(cov_m)
            else:
                st.caption("No historical coverage metrics snapshot available.")
    else:
        st.info("Select a news source above to inspect registry profile.")
