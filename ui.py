
import streamlit as st

def inject():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700&display=swap');
        html, body, [class*="css"]  { font-family: 'Instrument Sans', sans-serif; }
        .pill {display:inline-block;padding:6px 10px;border-radius:999px;background:#f3e8ff;color:#4a148c;margin-right:6px;font-weight:600}
        </style>
        """,
        unsafe_allow_html=True
    )
