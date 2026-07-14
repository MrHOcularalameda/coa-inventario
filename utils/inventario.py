"""
Administración de inventario: alta de nuevas piezas y ajuste manual
de existencias para armazones, lentes de contacto y accesorios.
"""

import streamlit as st


def _cargar_catalogo(sb, tabla):
    return sb.table(tabla).select("id,nombre").eq("activo", True).order("nombre").execute().data


def _seccion_armazones(sb):
    st.subheader("Armazones")

    marcas = _cargar_catalogo(sb, "marcas")
    proveedores = _cargar_catalogo(sb, "proveedores")

    if not marcas or not proveedores:
        st.warning("Primero agrega al menos una marca y un proveedor en la pestaña Catálogos.")
        return

    with st.expander("➕ Dar de alta un armazón nuevo"):
        with st.form("form_nuevo_armazon", clear_on_submit=True):
            col1, col2 = st.columns(2)
            marca_sel = col1.selectbox("Marca", [m["nombre"] for m in marcas])
            proveedor_sel = col2.selectbox("Proveedor", [p["nombre"] for p in proveedores])

            tipo_sel = st.selectbox("Tipo (rango)", ["marca", "linea", "basico"],
                                     format_func=lambda t: {"marca": "Marca (diseñador)", "linea": "Línea", "basico": "Básico"}[t])

            col3, col4 = st.columns(2)
            codigo = col3.text_input("Código de modelo (del fabricante)")
            color = col4.text_input("Color")

            col5, col6 = st.columns(2)
            estilo = col5.text_input("Estilo")
            existencias = col6.number_input("Existencias", min_value=0, step=1, value=1)

            enviado = st.form_submit_button("Guardar armazón")

            if enviado:
                if not codigo.strip():
                    st.error("El código es obligatorio.")
                else:
                    marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)
                    proveedor_id = next(p["id"] for p in proveedores if p["nombre"] == proveedor_sel)
                    try:
                        sb.table("armazones").insert({
                            "codigo": codigo.strip(),
                            "tipo": tipo_sel,
                            "marca_id": marca_id,
                            "proveedor_id": proveedor_id,
                            "color": color.strip() or None,
                            "estilo": estilo.strip() or None,
                            "existencias": int(existencias),
                        }).execute()
                        st.success("Armazón agregado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo guardar (¿ya existe ese código+color?): {e}")

    st.divider()
    st.write("**Inventario actual**")

    filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos", "marca", "linea", "basico"], key="filtro_tipo_armazon")

    query = sb.table("armazones").select("id,codigo,tipo,color,estilo,existencias,marcas(nombre)")
    if filtro_tipo != "Todos":
        query = query.eq("tipo", filtro_tipo)
    armazones = query.order("codigo").execute().data

    if not armazones:
        st.info("No hay armazones registrados con ese filtro.")
        return

    for a in armazones:
        col1, col2, col3 = st.columns([4, 2, 2])
        marca_nombre = a["marcas"]["nombre"] if a.get("marcas") else "—"
        col1.write(f'{marca_nombre} · {a["codigo"]} · {a.get("color") or "s/color"} · {a.get("estilo") or "s/estilo"} · ({a["tipo"]})')
        nueva_existencia = col2.number_input(
            "Existencias", min_value=0, value=int(a["existencias"]), key=f'exist_arm_{a["id"]}', label_visibility="collapsed"
        )
        if col3.button("Actualizar", key=f'upd_arm_{a["id"]}'):
            sb.table("armazones").update({"existencias": int(nueva_existencia)}).eq("id", a["id"]).execute()
            st.success("Actualizado.")
            st.rerun()


def _seccion_lentes_contacto(sb):
    st.subheader("Lentes de contacto")

    marcas = _cargar_catalogo(sb, "marcas")
    proveedores = _cargar_catalogo(sb, "proveedores")

    if not marcas or not proveedores:
        st.warning("Primero agrega al menos una marca y un proveedor en la pestaña Catálogos.")
        return

    with st.expander("➕ Dar de alta lentes de contacto nuevos"):
        with st.form("form_nuevo_lente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            marca_sel = col1.selectbox("Marca", [m["nombre"] for m in marcas])
            proveedor_sel = col2.selectbox("Proveedor", [p["nombre"] for p in proveedores])

            col3, col4 = st.columns(2)
            diseno = col3.text_input("Diseño (ej. Oasys, Biofinity)")
            existencias = col4.number_input("Existencias", min_value=0, step=1, value=1)

            enviado = st.form_submit_button("Guardar")

            if enviado:
                if not diseno.strip():
                    st.error("El diseño es obligatorio.")
                else:
                    marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)
                    proveedor_id = next(p["id"] for p in proveedores if p["nombre"] == proveedor_sel)
                    try:
                        sb.table("lentes_contacto").insert({
                            "marca_id": marca_id,
                            "proveedor_id": proveedor_id,
                            "diseno": diseno.strip(),
                            "existencias": int(existencias),
                        }).execute()
                        st.success("Lentes de contacto agregados.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo guardar (¿ya existe esa combinación?): {e}")

    st.divider()
    st.write("**Inventario actual**")

    lentes = sb.table("lentes_contacto").select("id,diseno,existencias,marcas(nombre)").order("diseno").execute().data

    if not lentes:
        st.info("No hay lentes de contacto registrados.")
        return

    for l in lentes:
        col1, col2, col3 = st.columns([4, 2, 2])
        marca_nombre = l["marcas"]["nombre"] if l.get("marcas") else "—"
        col1.write(f'{marca_nombre} · {l["diseno"]}')
        nueva_existencia = col2.number_input(
            "Existencias", min_value=0, value=int(l["existencias"]), key=f'exist_lc_{l["id"]}', label_visibility="collapsed"
        )
        if col3.button("Actualizar", key=f'upd_lc_{l["id"]}'):
            sb.table("lentes_contacto").update({"existencias": int(nueva_existencia)}).eq("id", l["id"]).execute()
            st.success("Actualizado.")
            st.rerun()


def _seccion_accesorios(sb):
    st.subheader("Accesorios")

    categorias = _cargar_catalogo(sb, "categorias_accesorios")
    proveedores = _cargar_catalogo(sb, "proveedores")

    if not categorias or not proveedores:
        st.warning("Primero agrega al menos una categoría y un proveedor en la pestaña Catálogos.")
        return

    with st.expander("➕ Dar de alta un accesorio nuevo"):
        with st.form("form_nuevo_accesorio", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cat_sel = col1.selectbox("Categoría", [c["nombre"] for c in categorias])
            proveedor_sel = col2.selectbox("Proveedor", [p["nombre"] for p in proveedores])

            col3, col4 = st.columns(2)
            descripcion = col3.text_input("Descripción (ej. Renu 60 ml)")
            existencias = col4.number_input("Existencias", min_value=0, step=1, value=1)

            enviado = st.form_submit_button("Guardar")

            if enviado:
                if not descripcion.strip():
                    st.error("La descripción es obligatoria.")
                else:
                    cat_id = next(c["id"] for c in categorias if c["nombre"] == cat_sel)
                    proveedor_id = next(p["id"] for p in proveedores if p["nombre"] == proveedor_sel)
                    try:
                        sb.table("accesorios").insert({
                            "categoria_id": cat_id,
                            "proveedor_id": proveedor_id,
                            "descripcion": descripcion.strip(),
                            "existencias": int(existencias),
                        }).execute()
                        st.success("Accesorio agregado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo guardar (¿ya existe esa combinación?): {e}")

    st.divider()
    st.write("**Inventario actual**")

    accesorios = (
        sb.table("accesorios")
        .select("id,descripcion,existencias,categorias_accesorios(nombre,alerta_stock_minimo)")
        .order("descripcion")
        .execute()
        .data
    )

    if not accesorios:
        st.info("No hay accesorios registrados.")
        return

    for a in accesorios:
        cat = a.get("categorias_accesorios") or {}
        alerta = cat.get("alerta_stock_minimo")
        bajo_stock = alerta is not None and a["existencias"] <= alerta

        col1, col2, col3 = st.columns([4, 2, 2])
        etiqueta = f'{cat.get("nombre", "—")} · {a["descripcion"]}'
        if bajo_stock:
            col1.write(f"🔴 {etiqueta} (¡stock bajo!)")
        else:
            col1.write(etiqueta)
        nueva_existencia = col2.number_input(
            "Existencias", min_value=0, value=int(a["existencias"]), key=f'exist_acc_{a["id"]}', label_visibility="collapsed"
        )
        if col3.button("Actualizar", key=f'upd_acc_{a["id"]}'):
            sb.table("accesorios").update({"existencias": int(nueva_existencia)}).eq("id", a["id"]).execute()
            st.success("Actualizado.")
            st.rerun()


def mostrar_inventario(sb):
    st.title("📦 Inventario")

    tab1, tab2, tab3 = st.tabs(["Armazones", "Lentes de contacto", "Accesorios"])

    with tab1:
        _seccion_armazones(sb)
    with tab2:
        _seccion_lentes_contacto(sb)
    with tab3:
        _seccion_accesorios(sb)
