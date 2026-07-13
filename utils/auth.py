"""
Autenticación simple de dos usuarios fijos (admin / ventas), con
credenciales guardadas en Streamlit Secrets. No hay altas dinámicas
de usuarios: si en el futuro se necesita un tercer usuario, se agrega
directamente en secrets.toml.
"""

import streamlit as st


def login_form():
    """Muestra el formulario de login. Devuelve True si ya hay sesión iniciada."""
    if st.session_state.get("autenticado"):
        return True

    st.title("👓 Centro Ocular Alameda — Inventario")
    st.subheader("Iniciar sesión")

    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        enviado = st.form_submit_button("Entrar")

    if enviado:
        usuarios = st.secrets["usuarios"]

        if usuario == usuarios["admin_usuario"] and contrasena == usuarios["admin_password"]:
            st.session_state["autenticado"] = True
            st.session_state["rol"] = "admin"
            st.session_state["nombre_usuario"] = usuarios.get("admin_nombre", "Administrador")
            st.rerun()

        elif usuario == usuarios["ventas_usuario"] and contrasena == usuarios["ventas_password"]:
            st.session_state["autenticado"] = True
            st.session_state["rol"] = "ventas"
            st.session_state["nombre_usuario"] = usuarios.get("ventas_nombre", "Ventas")
            st.rerun()

        else:
            st.error("Usuario o contraseña incorrectos")

    return False


def logout_button():
    with st.sidebar:
        st.write(f"Sesión: **{st.session_state.get('nombre_usuario', '')}**")
        if st.button("Cerrar sesión"):
            for key in ["autenticado", "rol", "nombre_usuario"]:
                st.session_state.pop(key, None)
            st.rerun()
