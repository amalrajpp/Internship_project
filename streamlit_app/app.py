import streamlit as st
from api_client import login, list_meetings, get_meeting, upload_meeting, rag_query, APIError
import pandas as pd
from io import BytesIO
import altair as alt

st.set_page_config(page_title="Meetings Dashboard", layout="wide")

# --- Authentication helpers ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "selected_meeting" not in st.session_state:
    st.session_state["selected_meeting"] = None


def require_login():
    if not st.session_state.get("token"):
        st.warning("Please log in from the sidebar to access data.")
        return False
    return True


# Sidebar
st.sidebar.title("Meetings Dashboard")
page = st.sidebar.radio("Go to", ["Login", "Upload Meeting", "Meetings", "Meeting Details", "RAG Assistant", "Settings"])

# Login page
if page == "Login":
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            resp = login(username, password)
            token = resp.get("access_token") or resp.get("token") or resp
            st.session_state["token"] = token
            st.success("Logged in")
        except APIError as e:
            st.error(f"Login failed: {e}")

# Upload
elif page == "Upload Meeting":
    st.header("Upload Meeting")
    if not require_login():
        st.stop()
    uploaded_file = st.file_uploader("Upload transcript or meeting audio (optional metadata supported)")
    title = st.text_input("Meeting title")
    date = st.date_input("Meeting date")
    if st.button("Upload") and uploaded_file:
        try:
            # Ensure we pass a file-like to requests
            file_bytes = uploaded_file.read()
            file_obj = (uploaded_file.name, BytesIO(file_bytes), uploaded_file.type)
            metadata = {"title": title, "date": str(date)}
            resp = upload_meeting(file_obj, metadata=metadata, token=st.session_state.get("token"))
            st.success("Upload successful")
            st.json(resp)
        except APIError as e:
            st.error(f"Upload failed: {e}")

# Meetings list + filters
elif page == "Meetings":
    st.header("Meetings")
    if not require_login():
        st.stop()
    with st.spinner("Fetching meetings..."):
        try:
            meetings = list_meetings(token=st.session_state.get("token"))
        except APIError as e:
            st.error(f"Failed to fetch meetings: {e}")
            st.stop()

    # Expecting meetings as list of dicts
    df = pd.DataFrame(meetings)
    st.sidebar.subheader("Filters")
    if df.empty:
        st.write("No meetings returned from the API.")
    else:
        # Basic filters
        q = st.sidebar.text_input("Search meetings (title, participant)")
        per_page = st.sidebar.number_input("Per page", min_value=5, max_value=50, value=10)
        page_num = st.sidebar.number_input("Page", min_value=1, value=1)

        filtered = df
        if q:
            ql = q.lower()
            filtered = filtered[filtered.apply(lambda r: ql in str(r.get("title", "")).lower() or ql in str(r.get("participants", "")).lower(), axis=1)]

        total = len(filtered)
        start = (page_num - 1) * per_page
        end = start + per_page
        st.write(f"Showing {start+1}-{min(end,total)} of {total}")
        st.dataframe(filtered.iloc[start:end])

        # Meeting selection
        meeting_options = filtered.get("id", filtered.index).tolist()
        meeting_id = st.selectbox("Select meeting ID", options=meeting_options)
        if st.button("Open meeting"):
            st.session_state["selected_meeting"] = meeting_id
            st.experimental_rerun()

# Dedicated Meeting Details page
elif page == "Meeting Details":
    st.header("Meeting Details")
    if not require_login():
        st.stop()
    mid = st.session_state.get("selected_meeting")
    if not mid:
        st.info("Select a meeting from the Meetings page first.")
        st.stop()

    try:
        details = get_meeting(mid, token=st.session_state.get("token"))
    except APIError as e:
        st.error(f"Failed to fetch meeting: {e}")
        st.stop()

    # Top-level info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(details.get("title") or details.get("name") or "Untitled")
        st.write("Date:", details.get("date"))
        st.write("Participants:", ", ".join([p.get("name") for p in details.get("participants", [])]) if details.get("participants") else "None")
    with col2:
        analytics = details.get("analytics") or {}
        if analytics:
            st.metric("Duration (min)", analytics.get("duration_minutes"))
            st.metric("Speakers", analytics.get("speaker_count"))

    # Flow: Transcript -> Summary -> Decisions -> Action Items -> Analytics
    st.markdown("---")
    # Transcript viewer with search
    with st.expander("Transcript", expanded=True):
        transcript = details.get("transcript") or details.get("text") or ""
        search_term = st.text_input("Search transcript")
        if search_term:
            lines = transcript.splitlines()
            matches = [ln for ln in lines if search_term.lower() in ln.lower()]
            if matches:
                for ln in matches:
                    st.markdown(f"- {ln}")
            else:
                st.write("No matches in transcript.")
        else:
            st.text_area("Full transcript", value=transcript, height=300)

    with st.expander("Summary", expanded=False):
        st.write(details.get("summary") or "No summary available")

    with st.expander("Decisions", expanded=False):
        decs = details.get("decisions") or []
        if decs:
            for d in decs:
                st.write(f"- {d}")
        else:
            st.write("No decisions recorded")

    with st.expander("Action Items", expanded=False):
        ais = details.get("action_items") or details.get("actions") or []
        if ais:
            ais_df = pd.DataFrame(ais)
            st.dataframe(ais_df)
        else:
            st.write("No action items")

    with st.expander("Analytics", expanded=False):
        if analytics:
            st.json(analytics)
            # Simple chart if duration present
            if analytics.get("duration_minutes") is not None:
                df_a = pd.DataFrame([{"metric": "duration_minutes", "value": analytics.get("duration_minutes")}, {"metric": "speaker_count", "value": analytics.get("speaker_count") or 0}])
                chart = alt.Chart(df_a).mark_bar().encode(x="metric", y="value")
                st.altair_chart(chart, use_container_width=True)
        else:
            st.write("No analytics available")

# RAG Assistant
elif page == "RAG Assistant":
    st.header("AI Assistant (RAG)")
    if not require_login():
        st.stop()
    question = st.text_area("Ask a question about your meetings")
    top_k = st.slider("Top K meetings to retrieve", 1, 10, 5)
    if st.button("Ask") and question:
        with st.spinner("Retrieving relevant meetings and generating answer..."):
            try:
                resp = rag_query(question, token=st.session_state.get("token"), top_k=top_k)
            except APIError as e:
                st.error(f"RAG query failed: {e}")
                st.stop()
        # Expecting: {answer: str, sources: [{meeting_id, date, snippet}]}
        st.subheader("Answer")
        st.write(resp.get("answer") or resp.get("result") or resp)
        st.subheader("Sources")
        for s in resp.get("sources", []):
            st.write(f"Meeting ID: {s.get('meeting_id') or s.get('id')}")
            st.write(f"Date: {s.get('date')}")
            st.write(f"Snippet: {s.get('snippet') or s.get('context')}")

# Settings
elif page == "Settings":
    st.header("Settings")
    st.write("API base URL is read from environment variable `API_BASE_URL`.")
    st.write("Current token: ", "set" if st.session_state.get("token") else "not set")
    if st.button("Log out"):
        st.session_state["token"] = None
        st.session_state["selected_meeting"] = None
        st.success("Logged out")
