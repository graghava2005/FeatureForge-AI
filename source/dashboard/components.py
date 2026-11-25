"""Reusable UI components for the white-and-orange FeatureForge AI Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

from config.settings import DESIGN_COLORS


def inject_theme_css() -> None:
    c = DESIGN_COLORS
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {c["background"]};
            color: {c["primary_text"]};
        }}
        section[data-testid="stSidebar"] {{
            background-color: #FAFAFA;
            border-right: 1px solid {c["border"]};
        }}
        h1, h2, h3, h4 {{
            color: {c["primary_text"]} !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }}
        .ff-subtitle {{
            color: {c["secondary_text"]};
            font-size: 0.96rem;
            margin-top: -0.4rem;
            margin-bottom: 1.2rem;
        }}
        .ff-card {{
            background-color: {c["background"]};
            border: 1px solid {c["border"]};
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.9rem;
        }}
        .ff-card-accent {{
            background-color: {c["light_orange"]};
            border: 1px solid #FED7AA;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.9rem;
        }}
        .ff-metric-label {{
            color: {c["secondary_text"]};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }}
        .ff-metric-value {{
            color: {c["primary_text"]};
            font-size: 1.55rem;
            font-weight: 700;
            margin-top: 0.2rem;
        }}
        .ff-badge {{
            display: inline-block;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid transparent;
        }}
        .ff-badge-orange {{
            background-color: {c["light_orange"]};
            color: #C2410C;
            border-color: #FDBA74;
        }}
        .ff-badge-pass {{
            background-color: {c["success_bg"]};
            color: {c["success"]};
            border-color: #BBF7D0;
        }}
        .ff-badge-fail {{
            background-color: {c["error_bg"]};
            color: {c["error"]};
            border-color: #FECACA;
        }}
        .ff-badge-warn {{
            background-color: {c["warning_bg"]};
            color: {c["warning"]};
            border-color: #FDE68A;
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {c["primary_orange"]} !important;
            border-color: {c["primary_orange"]} !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: #EA580C !important;
            border-color: #EA580C !important;
        }}
        div.stButton > button[kind="secondary"] {{
            background-color: #FFFFFF !important;
            border: 1px solid {c["border"]} !important;
            color: {c["primary_text"]} !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, subtext: str = "") -> None:
    sub_html = (
        f'<div style="color:#666666;font-size:0.8rem;margin-top:0.2rem;">{subtext}</div>'
        if subtext
        else ""
    )
    st.markdown(
        f"""
        <div class="ff-card">
            <div class="ff-metric-label">{label}</div>
            <div class="ff-metric-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text: str, kind: str = "orange") -> str:
    cls = {
        "orange": "ff-badge ff-badge-orange",
        "pass": "ff-badge ff-badge-pass",
        "fail": "ff-badge ff-badge-fail",
        "warn": "ff-badge ff-badge-warn",
    }.get(kind, "ff-badge ff-badge-orange")
    return f'<span class="{cls}">{text}</span>'
