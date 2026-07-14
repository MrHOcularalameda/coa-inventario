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


def _mostrar_micas(sb):
    st.subheader("Micas / lentes oftálmicas")
    st.caption(
        "No manejan existencias — se piden según la graduación de cada paciente. "
        "Aquí solo defines qué opciones le aparecen a Andrea al vender un armazón."
    )
    _mostrar_catalogo(sb, "micas", "Micas")


def _mostrar_disenos_lentes_contacto(sb):
    st.subheader("Diseños de lentes de contacto")
    st.caption(
        "Estos no manejan existencias — se venden sobre pedido. Aquí solo defines "
        "qué combinaciones de marca + diseño le aparecen a Andrea como opción de venta."
    )

    marcas = sb.table("marcas_lc").select("id,nombre").eq("activo", True).order("nombre").execute().data
    proveedores = sb.table("proveedores").select("id,nombre").eq("activo", True).order("nombre").execute().data
    if not marcas or not proveedores:
        st.warning("Primero agrega al menos una marca (pestaña 'Marcas LC') y un proveedor.")
        return

    lentes = sb.table("lentes_contacto").select("id,diseno,activo,marcas_lc(nombre)").order("diseno").execute().data

    if lentes:
        for l in lentes:
            col1, col2 = st.columns([4, 1])
            marca_nombre = l["marcas_lc"]["nombre"] if l.get("marcas_lc") else "—"
            col1.write(f'{marca_nombre} · {l["diseno"]}')
            etiqueta_boton = "Desactivar" if l["activo"] else "Activar"
            if col2.button(etiqueta_boton, key=f'lc_{l["id"]}'):
                sb.table("lentes_contacto").update({"activo": not l["activo"]}).eq("id", l["id"]).execute()
                st.rerun()
    else:
        st.info("Todavía no hay diseños registrados.")

    with st.form("form_nuevo_diseno_lc", clear_on_submit=True):
        st.write("Agregar nuevo diseño")
        marca_sel = st.selectbox("Marca", [m["nombre"] for m in marcas])
        proveedor_sel = st.selectbox("Proveedor", [p["nombre"] for p in proveedores])
        diseno = st.text_input("Diseño (ej. Oasys, Biofinity)")
        enviado = st.form_submit_button("Agregar")

        if enviado:
            if not diseno.strip():
                st.error("El diseño no puede estar vacío.")
            else:
                marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)
                proveedor_id = next(p["id"] for p in proveedores if p["nombre"] == proveedor_sel)
                try:
                    sb.table("lentes_contacto").insert({
                        "marca_lc_id": marca_id,
                        "proveedor_id": proveedor_id,
                        "diseno": diseno.strip(),
                    }).execute()
                    st.success("Diseño agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo agregar (¿ya existe esa combinación?): {e}")


def mostrar_catalogos(sb):
    st.title("📋 Catálogos")
    st.caption(
        "Aquí administras las listas fijas que usan los formularios de venta e inventario. "
        "Desactivar un registro no borra el historial de ventas ya hechas con él, "
        "solo deja de aparecer como opción nueva."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["Proveedores", "Marcas (armazones)", "Marcas (LC)", "Categorías de accesorios",
         "Responsables", "Diseños de lentes de contacto", "Micas"]
    )

    with tab1:
        _mostrar_catalogo(sb, "proveedores", "Proveedores")

    with tab2:
        _mostrar_catalogo(sb, "marcas", "Marcas de armazones")

    with tab3:
        _mostrar_catalogo(sb, "marcas_lc", "Marcas de lentes de contacto")

    with tab4:
        _mostrar_catalogo(
            sb,
            "categorias_accesorios",
            "Categorías de accesorios",
            campo_extra={"campo": "alerta_stock_minimo", "etiqueta": "Alerta si baja de"},
        )

    with tab5:
        _mostrar_catalogo(sb, "responsables", "Responsables")

    with tab6:
        _mostrar_disenos_lentes_contacto(sb)

    with tab7:
        _mostrar_micas(sb)
