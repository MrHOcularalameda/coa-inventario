import os
import streamlit as st
from utils.auth import login_form, logout_button
from utils.supabase_client import get_supabase_client
from utils.venta import mostrar_formulario_venta
from utils.inventario import mostrar_inventario
from utils.catalogos import mostrar_catalogos

st.set_page_config(
    page_title="COA — Inventario",
    page_icon="👓",
    layout="wide",
)

if not login_form():
    st.stop()

if os.path.exists("assets/logo.png"):
    st.sidebar.image("assets/logo.png", width=140)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #0F2438;
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] img {
        border-radius: 50%;
        object-fit: cover;
        width: 100px;
        height: 100px;
        display: block;
        margin: 0 auto;
    }
    [data-testid="stSidebar"] button {
        background-color: #1B3A5C !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #2C5480 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

logout_button()

st.markdown(
    "<h2 style='text-align: center;'>Sistema de Gestión de Inventarios</h2>",
    unsafe_allow_html=True,
)

sb = get_supabase_client()
rol = st.session_state["rol"]

if rol == "admin":
    seccion = st.sidebar.radio("Sección", ["Inventario", "Catálogos", "Auditor"])

    if seccion == "Inventario":
        mostrar_inventario(sb)
    elif seccion == "Catálogos":
        mostrar_catalogos(sb)
    elif seccion == "Auditor":
        st.title("📊 Auditor")
        st.info("Aquí va el módulo de reportes — siguiente paso")

elif rol == "ventas":
    mostrar_formulario_venta(sb)
