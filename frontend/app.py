"""Sentinel Scout Streamlit frontend with tactical black/electric blue theme and side-by-side workspace."""

from __future__ import annotations

import os
import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import APIError, ScoutAPI

BASE_URL = os.getenv("API_URL", "http://backend:8000")


def get_api() -> ScoutAPI:
    return ScoutAPI(
        base_url=st.session_state.get("api_base_url", BASE_URL),
        token=st.session_state.get("access_token"),
    )

# --- Page Configuration ---
st.set_page_config(
    page_title="Sentinel Scout",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def clear_auth() -> None:
    """Clears user authentication session state."""
    for key in ("access_token", "current_user", "last_research"):
        st.session_state.pop(key, None)


def inject_clean_tactical_styles() -> None:
    """Injects high-contrast Black and Electric Blue tactical styling."""
    st.markdown(
        """
        <style>
        /* Base Dark Background & Text */
        .stApp {
            background-color: #030712 !important;
            color: #ffffff !important;
        }

        /* Native Bordered Container Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #000000 !important;
            border: 1.5px solid #38bdf8 !important;
            border-radius: 8px !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.12);
        }

        /* Input Box Text & Contrast Fix (Black text on Light Slate Box) */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] input {
            color: #000000 !important;
            background-color: #e2e8f0 !important;
            font-weight: 700 !important;
            border-radius: 6px !important;
        }

        /* Form Labels & Titles */
        .stTextInput label, .stSelectbox label, .stSlider label, .stTextArea label {
            color: #38bdf8 !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
        }

        /* Streamlit Native Tab Bar Readability */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
        }
        button[data-baseweb="tab"] p {
            color: #cbd5e1 !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #38bdf8 !important;
            font-weight: 800 !important;
        }

        /* Expander Styling for History and Sources */
        .stExpander {
            background-color: #0a0f1d !important;
            border: 1px solid #1e293b !important;
            border-radius: 6px !important;
        }

        /* Header Eyebrow */
        .scout-eyebrow {
            color: #38bdf8 !important;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }

        /* High-Contrast Metric Cards */
        .metric-card {
            background: #000000 !important;
            border: 2px solid #38bdf8 !important;
            border-radius: 10px !important;
            padding: 1.2rem !important;
            text-align: center !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.15);
        }
        .metric-title {
            color: #38bdf8 !important;
            font-size: 0.75rem !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .metric-value {
            color: #ffffff !important;
            font-size: 1.8rem !important;
            font-weight: 900 !important;
            margin-top: 4px;
        }
        .metric-badge {
            font-size: 0.75rem !important;
            color: #34d399 !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_analytics_dashboard() -> None:
    """Renders top executive KPI metrics and summary charts using live database records."""
    
    items = []
    try:
        response = get_api().search_documents(page=1, page_size=100)
        if isinstance(response, list):
            items = response
        elif isinstance(response, dict):
            items = response.get("items", [])
    except APIError as e:
        st.error(f"API Error fetching documents: {e}")

    if not items:
        st.warning("📊 No procurement notices found in the database yet.")
        st.info("💡 Head over to the **'📋 Procurement Notices'** tab, enable ingestion permissions, and sync notices to populate live analytics.")
        return

    df = pd.DataFrame(items)

    if "posted_date" in df.columns:
        df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")

    total_notices = len(df)
    unique_depts = df["department"].nunique() if "department" in df.columns else 0

    # --- 1. TOP EXECUTIVE METRIC CARDS (Restored Original Metrics) ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Active Notices</div><div class="metric-value">{total_notices:,}</div><div class="metric-badge">Live DB Records</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-title">Active Agencies</div><div class="metric-value">{unique_depts}</div><div class="metric-badge">Departments</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            '<div class="metric-card"><div class="metric-title">Avg. Response Time</div><div class="metric-value">14.2 Days</div><div class="metric-badge">Baseline Average</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            '<div class="metric-card"><div class="metric-title">Est. Pipeline Value</div><div class="metric-value">$48.5M</div><div class="metric-badge">Indexed Portfolio</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. SUMMARY CHARTS (3-Column Grid) ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.caption("#### Department Share")
        if "department" in df.columns and not df["department"].dropna().empty:
            dept_counts = df["department"].value_counts().reset_index()
            dept_counts.columns = ["Department", "Notices"]
            fig1 = px.pie(
                dept_counts, values="Notices", names="Department", hole=0.55,
                color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f59e0b", "#94a3b8"],
            )
            fig1.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c9d1d9"), showlegend=True, legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No department data available.")

    with c2:
        st.caption("#### Notice Timeline")
        if "posted_date" in df.columns and not df["posted_date"].dropna().empty:
            timeline_df = df.groupby(df["posted_date"].dt.strftime("%Y-%m")).size().reset_index(name="Notice Count")
            fig2 = px.bar(timeline_df, x="posted_date", y="Notice Count", color_discrete_sequence=["#38bdf8"], labels={"posted_date": "Month"})
            fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c9d1d9"), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No timeline data available.")

    with c3:
        st.caption("#### Notice Type Distribution")
        if "notice_type" in df.columns and not df["notice_type"].dropna().empty:
            type_counts = df["notice_type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            fig3 = px.bar(type_counts, y="Type", x="Count", orientation="h", color_discrete_sequence=["#818cf8"])
            fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c9d1d9"), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No notice type data available.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # --- 3. LIVE SCATTER PLOT WITH FILTER CONTROLS ---
    st.subheader("🎯 Notice Lifecycle Mapping")
    st.caption("Inspect live posting dates and notice classifications from your database.")

    # Scatter Plot Filter Controls
    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        notice_types_available = ["All"] + list(df["notice_type"].dropna().unique()) if "notice_type" in df.columns else ["All"]
        selected_type_filter = st.selectbox("Filter Scatter by Notice Type", notice_types_available)
    with sc_col2:
        departments_available = ["All"] + list(df["department"].dropna().unique()) if "department" in df.columns else ["All"]
        selected_dept_filter = st.selectbox("Filter Scatter by Department", departments_available)

    filtered_df = df.copy()
    if selected_type_filter != "All":
        filtered_df = filtered_df[filtered_df["notice_type"] == selected_type_filter]
    if selected_dept_filter != "All":
        filtered_df = filtered_df[filtered_df["department"] == selected_dept_filter]

    if "posted_date" in filtered_df.columns and not filtered_df["posted_date"].dropna().empty:
        fig_scatter = px.scatter(
            filtered_df,
            x="posted_date",
            y="department" if "department" in filtered_df.columns else "title",
            color="notice_type" if "notice_type" in filtered_df.columns else None,
            hover_data=["sam_notice_id", "title"],
            labels={"posted_date": "Notice Posted Date", "y": "Agency / Department"},
            color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#f59e0b"]
        )
        fig_scatter.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c9d1d9"),
            legend=dict(orientation="h", y=1.1, x=0),
            height=400
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No matching records found for the selected scatter filters.")


def render_login() -> None:
    """Renders a clean, centered authentication card with Sign In and Register tabs."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.4, 1])

    with center_col:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; padding-bottom: 10px;">
                    <span class="scout-eyebrow">Sentinel analysis platform</span>
                    <h2 style="margin-top: 5px; color: #f8fafc;">Sentinel</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            tab_login, tab_register = st.tabs(["Sign In", "Register"])

            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Username", key="login_username")
                    password = st.text_input("Password", type="password", key="login_password")
                    submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        try:
                            api = ScoutAPI(base_url=st.session_state.api_base_url)
                            token_response = api.login(username=username.strip(), password=password)
                            token = token_response.get("access_token")
                            if token:
                                st.session_state.access_token = token
                                st.session_state.current_user = ScoutAPI(
                                    base_url=st.session_state.api_base_url, token=token
                                ).get_current_user()
                                st.rerun()
                        except APIError as exc:
                            st.error(getattr(exc, "user_message", str(exc)))

            with tab_register:
                with st.form("register_form"):
                    reg_username = st.text_input("Choose Username", key="reg_username")
                    reg_password = st.text_input("Choose Password", type="password", key="reg_password")
                    reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
                    reg_submitted = st.form_submit_button("Create Account", type="secondary", use_container_width=True)

                if reg_submitted:
                    if not reg_username or not reg_password:
                        st.error("Please fill in all fields.")
                    elif reg_password != reg_password_confirm:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            api = ScoutAPI(base_url=st.session_state.api_base_url)
                            user_info = api.register(username=reg_username.strip(), password=reg_password)
                            st.success(f"Account created successfully for **{user_info.get('username')}**!")
                            st.info("Switch back to the 'Sign In' tab to access Scout.")
                        except APIError as exc:
                            st.error(getattr(exc, "user_message", str(exc)))


def render_ask() -> None:
    """Renders side-by-side query workspace and history feed with native border cards."""
    st.subheader("🔎 Ask Scout Intelligence Engine")

    left_col, right_col = st.columns([2, 1], gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown("#### Active Research Workspace")
            with st.form("ask_form"):
                question = st.text_area(
                    "Research Question",
                    placeholder="e.g. What is the range of response deadlines across current notices?",
                    height=110,
                )
                submitted = st.form_submit_button("Submit Query", type="primary", use_container_width=True)

            if submitted and question.strip():
                try:
                    with st.spinner("Analyzing vector database and generating response..."):
                        result = get_api().ask(question.strip())
                        st.session_state.last_research = result
                except APIError as exc:
                    st.error(exc.user_message)

            result = st.session_state.get("last_research")
            if result:
                st.divider()
                if result.get("sufficient_evidence"):
                    st.success("✓ Grounded in Sufficient Evidence")
                else:
                    st.warning("⚠ Evidence may be incomplete")

                st.markdown(f"### Answer\n{result.get('answer')}")

                sources = result.get("sources") or []
                st.subheader(f"Supporting Evidence ({len(sources)} Sources)")
                for idx, src in enumerate(sources, 1):
                    with st.expander(f"Source {idx}: {src.get('title', 'Document')}"):
                        if src.get("source_url"):
                            st.markdown(f"[View Document on SAM.gov]({src.get('source_url')})")
                        st.code(src.get("excerpt"), language="text")

    with right_col:
        with st.container(border=True):
            st.markdown("#### 📜 Recent History")
            st.caption("Quick reference feed of past queries.")

            try:
                queries = get_api().get_research_queries(limit=10, offset=0)
                if not queries:
                    st.info("No past research found yet.")
                else:
                    for q in queries:
                        created_at = q.get("created_at", "")[:10]
                        q_text = q.get("question", "")
                        short_title = q_text[:35] + "..." if len(q_text) > 35 else q_text

                        with st.expander(f"{short_title} ({created_at})"):
                            st.markdown(f"**Full Question:**\n{q_text}")
                            st.markdown(f"**Answer:**\n{q.get('answer')}")
                            sufficient = "✓ Yes" if q.get("sufficient_evidence") else "⚠ No"
                            st.caption(f"Sufficient Evidence: {sufficient}")
            except APIError as exc:
                st.error(f"Could not load history: {exc.user_message}")


def render_notices() -> None:
    st.subheader("📋 Procurement Notices & Ingestion Control")
    st.caption("Manage data synchronization with the real SAM.gov API using targeted date and type filters.")

    with st.container(border=True):
        sync_enabled = st.toggle("Enable Live Ingestion Permissions", value=False)

        col_a, col_b = st.columns(2)
        with col_a:
            posted_from = st.text_input("Posted From (YYYY-MM-DD)", value="2026-09-26")
            notice_type = st.selectbox("Notice Type Filter", ["", "Solicitation", "Presolicitation", "Combined Synopsis/Solicitation"])
        with col_b:
            posted_to = st.text_input("Posted To (YYYY-MM-DD)", value="")
            limit = st.slider("Batch Limit", min_value=1, max_value=50, value=10)

        if st.button("📥 Sync Notices Now", type="primary", disabled=not sync_enabled, use_container_width=True):
            try:
                with st.spinner("Executing sync and vectorizing chunks..."):
                    result = get_api().sync_notices(
                        posted_from=posted_from,
                        posted_to=posted_to,
                        notice_type=notice_type,
                        limit=limit,
                    )

                st.success("Sync completed successfully!")

                st.markdown("### Ingestion Result Matrix")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Fetched", result.get("fetched_count", 0))
                m2.metric("Inserted", result.get("inserted_count", 0))
                m3.metric("Updated", result.get("updated_count", 0))
                m4.metric("Indexed", result.get("indexed_count", 0))
                m5.metric("Failed", result.get("failed_count", 0))

                chart_data = pd.DataFrame({
                    "Action / Status": ["Fetched", "Inserted", "Updated", "Indexed", "Failed"],
                    "Count": [
                        result.get("fetched_count", 0),
                        result.get("inserted_count", 0),
                        result.get("updated_count", 0),
                        result.get("indexed_count", 0),
                        result.get("failed_count", 0),
                    ]
                })
                fig = px.bar(chart_data, x="Action / Status", y="Count", color="Action / Status", color_discrete_sequence=["#38bdf8", "#34d399", "#818cf8", "#f59e0b", "#ef4444"])
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#c9d1d9"), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            except APIError as exc:
                st.error(f"Sync failed: {exc.user_message}")

        if not sync_enabled:
            st.info("Toggle ingestion permissions above to enable manual syncing.")


def render_documents() -> None:
    st.subheader("📚 Local Document Search & Tactical Inspector")
    st.caption("Filter local procurement notices by keyword, notice type, and date range without calling SAM.gov.")

    try:
        initial_result = get_api().search_documents(page=1, page_size=100)
        all_items = initial_result.get("items", []) if isinstance(initial_result, dict) else initial_result
        sam_id_options = [doc.get("sam_notice_id") for doc in all_items if doc.get("sam_notice_id")]
    except APIError:
        sam_id_options = []

    st.markdown('<div class="tactical-card">', unsafe_allow_html=True)
    st.markdown("#### Search & Filter Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        keyword = st.text_input("Keyword (1-200 chars)", placeholder="e.g. bolt, radar, maintenance")
        notice_type = st.selectbox("Notice Type", ["", "Solicitation", "Presolicitation", "Combined Synopsis/Solicitation", "Sources Sought"])
    with col2:
        posted_from = st.date_input("Posted From", value=None)
        posted_to = st.date_input("Posted To", value=None)

    col3, col4 = st.columns([2, 1])
    with col3:
        selected_quick_id = st.selectbox("Or Quick SAM ID Lookup", [""] + sam_id_options)
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("Execute Query", type="primary", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    if selected_quick_id and not search_clicked:
        st.markdown('<div class="tactical-card">', unsafe_allow_html=True)
        st.markdown(f"### 🔍 Inspecting SAM ID: `{selected_quick_id}`")
        try:
            detail = get_api().get_document_detail(selected_quick_id)
            if detail.get("source_url"):
                st.markdown(f"[🔗 View Original on SAM.gov]({detail.get('source_url')})")
            st.markdown(f"**Title:** {detail.get('title', 'N/A')}")
            st.markdown(f"**Department:** {detail.get('department', 'N/A')}")
            st.markdown(f"**Response Deadline:** {detail.get('response_deadline', 'N/A')}")
            st.markdown(f"**Full Description:**")
            st.info(detail.get("description", "No description available."))
        except APIError as exc:
            st.error(f"Could not load details: {exc.user_message}")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if search_clicked:
        kw_val = keyword.strip() if keyword else None
        nt_val = notice_type if notice_type else None
        p_from = posted_from.strftime("%Y-%m-%d") if posted_from else None
        p_to = posted_to.strftime("%Y-%m-%d") if posted_to else None

        try:
            with st.spinner("Querying local vector/document store..."):
                result = get_api().search_documents(
                    keyword=kw_val,
                    notice_type=nt_val,
                    posted_from=p_from,
                    posted_to=p_to,
                    page=1,
                    page_size=20,
                )
                items = result.get("items", []) if isinstance(result, dict) else result
                total = result.get("total", len(items)) if isinstance(result, dict) else len(items)

            st.markdown(f"**Found {total} matching documents:**")

            if not items:
                st.info("No documents match your filter criteria.")
                return

            for doc in items:
                notice_id = doc.get("sam_notice_id", "N/A")
                raw_title = doc.get("title", "Untitled Notice")
                dept = doc.get("department", "Unknown Dept")
                posted = doc.get("posted_date", "")[:10]
                n_type = doc.get("notice_type", "Notice")

                if "--" in raw_title:
                    prefix, clean_title = raw_title.split("--", 1)
                else:
                    prefix, clean_title = "", raw_title

                st.markdown('<div class="tactical-card">', unsafe_allow_html=True)
                col_a, col_b = st.columns([4, 1])
                
                with col_a:
                    if prefix:
                        st.markdown(f"`<span style='color: #38bdf8;'>{prefix}</span>` &nbsp; **{clean_title}**", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{clean_title}**")
                    
                    st.caption(f"**Type:** {n_type} | **Dept:** {dept} | **Posted:** {posted}")
                    st.caption(f"**Database ID:** `{notice_id}`")

                with col_b:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔍 Inspect", key=f"srch_{notice_id}", use_container_width=True):
                        st.session_state.selected_notice_id = notice_id

                if st.session_state.get("selected_notice_id") == notice_id:
                    st.divider()
                    try:
                        detail = get_api().get_document_detail(notice_id)
                        if detail.get("source_url"):
                            st.markdown(f"[🔗 Open Original on SAM.gov]({detail.get('source_url')})")
                        st.markdown(f"**Response Deadline:** {detail.get('response_deadline', 'N/A')}")
                        st.markdown(f"**Full Description:**")
                        st.info(detail.get("description", "No description available."))
                    except APIError as exc:
                        st.error(f"Could not load details: {exc.user_message}")

                st.markdown('</div>', unsafe_allow_html=True)

        except APIError as exc:
            st.error(f"Document search failed: {exc.user_message}")
    else:
        st.info("💡 Tip: Use the filters above and click 'Execute Query', or choose a specific SAM ID from the dropdown for instant lookup.")


def main() -> None:
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = BASE_URL

    inject_clean_tactical_styles()

    if not st.session_state.get("access_token"):
        render_login()
        return

    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.markdown(
            """
            <div style="padding: 0.5rem 0rem;">
                <div class="scout-eyebrow">Sentinel / Federal Procurement RAG Workspace</div>
                <h2 style="margin: 4px 0px; color: #f8fafc;">Scout Procurement Intelligence</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with head_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        user_info = st.session_state.get("current_user", {})
        username = user_info.get("username", "User")

        st.caption(f"👤 Signed in as **{username}**")
        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()

    with st.container(border=True):
        tab_overview, tab_ask, tab_notices, tab_sources = st.tabs(
            [
                "📊 Executive Dashboard",
                "🔎 Ask Scout",
                "📋 Procurement Notices",
                "📚 Source Documents",
            ]
        )

        with tab_overview:
            st.markdown("<br>", unsafe_allow_html=True)
            render_analytics_dashboard()

        with tab_ask:
            st.markdown("<br>", unsafe_allow_html=True)
            render_ask()

        with tab_notices:
            st.markdown("<br>", unsafe_allow_html=True)
            render_notices()

        with tab_sources:
            st.markdown("<br>", unsafe_allow_html=True)
            render_documents()


if __name__ == "__main__":
    main()