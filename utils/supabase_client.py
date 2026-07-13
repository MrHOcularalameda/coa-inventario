"""
Cliente de Supabase por sesión.

IMPORTANTE: no usar un cliente global cacheado (@st.cache_resource a nivel
módulo) porque eso comparte la misma conexión entre todas las sesiones de
Streamlit, mezclando datos entre usuarios distintos conectados al mismo
tiempo. Cada sesión de navegador debe tener su propia instancia.
"""

import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Devuelve un cliente de Supabase único para esta sesión de navegador."""
    if "supabase_client" not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_role_key"]
        st.session_state["supabase_client"] = create_client(url, key)
    return st.session_state["supabase_client"]
