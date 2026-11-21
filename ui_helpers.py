"""Small compatibility layer so the app runs on both older and newer Streamlit versions
(use_container_width was replaced by width='stretch' in recent releases)."""
import inspect

import streamlit as st


def _stretch_kwargs(fn):
    params = inspect.signature(fn).parameters
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


def plot(fig, **kw):
    st.plotly_chart(fig, **_stretch_kwargs(st.plotly_chart), **kw)


def table(df, **kw):
    st.dataframe(df, **_stretch_kwargs(st.dataframe), **kw)
