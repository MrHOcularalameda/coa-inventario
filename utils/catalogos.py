"""
Administración de catálogos simples: proveedores, marcas,
categorias_accesorios, responsables.

Las cuatro tablas comparten la misma forma (id, nombre, activo), así
que se maneja con una sola función reutilizable en vez de repetir
código cuatro veces.
"""

import streamlit as st


def _mostrar_catalogo(sb, tabla: str, titulo: str, campo_extra: dict = None):
    """
    Muestra un catálogo simple con alta de nuevos registros y
    activar/desactivar existentes.

    campo_extra: dict opcional para catálogos con un campo adicional,
    por ejemplo categorias_accesorios con 'alerta_stock_minimo'.
    """
    st.subheader(titulo)

    registros = sb.table(tabla).select("*").order("nombre").execute().data

    if registros:
        for r in registros:
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(r["nombre"])
            if campo_extra:
                campo = campo_extra["campo"]
                valor = r.get(campo)
                col2.write(f'{campo_extra["etiqueta"]}: {valor if valor is not None else "—"}')
            estado_actual = r["activo"]
            etiqueta_boton = "Desactivar" if estado_actual else "Activar"
            if col3.button(etiqueta_boton, key=f"{tabla}_{r['id']}"):
                sb.table(tabla).update({"activo": not estado_actual}).eq("id", r["id"]).execute()
                st.rerun()
    else:
        st.info("Todavía no hay registros aquí.")

    with st.form(f"form_nuevo_{tabla}", clear_on_submit=True):
        st.write(f"Agregar nuevo en {titulo.lower()}")
        nombre_nuevo = st.text_input("Nombre", key=f"nombre_{tabla}")

        valor_extra = None
        if campo_extra:
            valor_extra = st.number_input(
                campo_extra["etiqueta"], min_value=0, step=1, key=f"extra_{tabla}"
            )

        enviado = st.form_submit_button("Agregar")

        if enviado:
            if not nombre_nuevo.strip():
                st.error("El nombre no puede estar vacío.")
            else:
                datos = {"nombre": nombre_nuevo.strip()}
                if campo_extra:
                    datos[campo_extra["campo"]] = int(valor_extra) if valor_extra else None
                try:
                    sb.table(tabla).insert(datos).execute()
                    st.success(f'"{nombre_nuevo.strip()}" agregado.')
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo agregar (¿ya existe ese nombre?): {e}")


def mostrar_catalogos(sb):
    st.title("📋 Catálogos")
    st.caption(
        "Aquí administras las listas fijas que usan los formularios de venta e inventario. "
        "Desactivar un registro no borra el historial de ventas ya hechas con él, "
        "solo deja de aparecer como opción nueva."
    )

    tab1, tab2, tab3, tab4 = st.tabs(["Proveedores", "Marcas", "Categorías de accesorios", "Responsables"])

    with tab1:
        _mostrar_catalogo(sb, "proveedores", "Proveedores")

    with tab2:
        _mostrar_catalogo(sb, "marcas", "Marcas")

    with tab3:
        _mostrar_catalogo(
            sb,
            "categorias_accesorios",
            "Categorías de accesorios",
            campo_extra={"campo": "alerta_stock_minimo", "etiqueta": "Alerta si baja de"},
        )

    with tab4:
        _mostrar_catalogo(sb, "responsables", "Responsables")
