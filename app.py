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

logout_button()

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
