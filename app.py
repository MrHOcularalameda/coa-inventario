import streamlit as st
from utils.auth import login_form, logout_button

st.set_page_config(
    page_title="COA — Inventario",
    page_icon="👓",
    layout="wide",
)

if not login_form():
    st.stop()

logout_button()

rol = st.session_state["rol"]

if rol == "admin":
    st.title("Panel de administración")
    seccion = st.sidebar.radio("Sección", ["Inventario", "Auditor"])

    if seccion == "Inventario":
        st.info("Aquí va el módulo de Inventario (armazones / accesorios) — siguiente paso")
    elif seccion == "Auditor":
        st.info("Aquí va el módulo de Auditor (reportes) — siguiente paso")

elif rol == "ventas":
    st.title("Registro de venta")
    st.info("Aquí va el formulario de venta para Andrea — siguiente paso")
