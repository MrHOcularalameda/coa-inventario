"""
Formulario de registro de venta (rol: ventas / Andrea).

Flujo:
1. Andrea va agregando artículos a un "carrito" temporal (armazones,
   lentes de contacto, accesorios o micas), eligiendo siempre de
   listas desplegables. Armazones y accesorios se limitan a lo que
   hay en existencia; lentes de contacto y micas se piden sobre
   pedido y no dependen de inventario.
2. Al final llena folio, responsable y total, y guarda todo el folio
   de un jalón. Cada artículo del carrito se inserta en venta_detalle,
   y el trigger de la base de datos descuenta el inventario donde
   aplica (armazones y accesorios únicamente).
"""

import streamlit as st


def _cargar_marcas(sb):
    return sb.table("marcas").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_marcas_lc(sb):
    return sb.table("marcas_lc").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_micas(sb):
    return sb.table("micas").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_responsables(sb):
    return sb.table("responsables").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_categorias_accesorios(sb):
    return sb.table("categorias_accesorios").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _input_precio_unitario(key_prefix):
    precio = st.number_input(
        "Precio unitario (opcional)", min_value=0.0, step=0.5, format="%.2f", key=f"{key_prefix}_precio"
    )
    if precio > 0:
        st.caption(f"${precio:,.2f}")
    return precio if precio > 0 else None


def _seccion_anteojos(sb):
    st.subheader("Agregar armazón")
    marcas = _cargar_marcas(sb)
    if not marcas:
        st.warning("No hay marcas registradas todavía.")
        return

    nombres_marca = [m["nombre"] for m in marcas]
    marca_sel = st.selectbox("Marca", nombres_marca, key="anteojos_marca")
    marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)

    armazones = (
        sb.table("armazones")
        .select("id,codigo,color,estilo,existencias")
        .eq("marca_id", marca_id)
        .gt("existencias", 0)
        .order("codigo")
        .execute()
        .data
    )

    if not armazones:
        st.info(f"No hay existencias disponibles de {marca_sel}.")
        return

    etiquetas = [
        f'{a["codigo"]} · {a.get("color") or "s/color"} · {a.get("estilo") or "s/estilo"} (disp: {a["existencias"]})'
        for a in armazones
    ]
    idx = st.selectbox("Modelo disponible", range(len(etiquetas)), format_func=lambda i: etiquetas[i], key="anteojos_modelo")
    armazon = armazones[idx]

    cantidad = st.number_input(
        "Cantidad", min_value=1, max_value=int(armazon["existencias"]), value=1, key="anteojos_cantidad"
    )

    precio_unitario = _input_precio_unitario("anteojos")

    st.divider()
    st.caption("¿Lleva mica? (opcional, no depende de inventario)")
    micas = _cargar_micas(sb)
    agregar_mica = False
    mica_sel = None
    precio_mica = None
    if micas:
        agregar_mica = st.checkbox("Agregar mica a esta venta", key="anteojos_agregar_mica")
        if agregar_mica:
            mica_sel = st.selectbox("Tipo de mica", [m["nombre"] for m in micas], key="anteojos_mica")
            precio_mica = _input_precio_unitario("anteojos_mica")
    else:
        st.caption("No hay micas dadas de alta todavía.")

    if st.button("➕ Agregar armazón a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "armazon",
            "armazon_id": armazon["id"],
            "descripcion": f'Armazón {marca_sel} {armazon["codigo"]}',
            "cantidad": int(cantidad),
            "precio_unitario": precio_unitario,
        })
        if agregar_mica and mica_sel:
            mica_id = next(m["id"] for m in micas if m["nombre"] == mica_sel)
            st.session_state.carrito.append({
                "tipo_articulo": "mica",
                "mica_id": mica_id,
                "descripcion": f"Mica: {mica_sel}",
                "cantidad": 1,
                "precio_unitario": precio_mica,
            })
        st.success("Armazón agregado")
        st.rerun()


def _seccion_lentes_contacto(sb):
    st.subheader("Agregar lentes de contacto")
    st.caption("Se venden sobre pedido — no manejan existencias en inventario.")
    marcas = _cargar_marcas_lc(sb)
    if not marcas:
        st.warning("No hay marcas de lentes de contacto registradas todavía.")
        return

    nombres_marca = [m["nombre"] for m in marcas]
    marca_sel = st.selectbox("Marca", nombres_marca, key="lc_marca")
    marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)

    lentes = (
        sb.table("lentes_contacto")
        .select("id,diseno")
        .eq("marca_lc_id", marca_id)
        .eq("activo", True)
        .order("diseno")
        .execute()
        .data
    )

    if not lentes:
        st.info(f"No hay diseños de {marca_sel} dados de alta. Pídele al administrador que lo agregue en Catálogos.")
        return

    etiquetas = [l["diseno"] for l in lentes]
    idx = st.selectbox("Diseño", range(len(etiquetas)), format_func=lambda i: etiquetas[i], key="lc_diseno")
    lente = lentes[idx]

    cantidad = st.number_input("Cantidad", min_value=1, value=1, key="lc_cantidad")
    precio_unitario = _input_precio_unitario("lc")

    if st.button("➕ Agregar lentes de contacto a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "lente_contacto",
            "lente_contacto_id": lente["id"],
            "descripcion": f'Lentes de contacto {marca_sel} {lente["diseno"]}',
            "cantidad": int(cantidad),
            "precio_unitario": precio_unitario,
        })
        st.success("Lentes de contacto agregados")
        st.rerun()


def _seccion_accesorios(sb):
    st.subheader("Agregar accesorio")
    categorias = _cargar_categorias_accesorios(sb)
    if not categorias:
        st.warning("No hay categorías de accesorios registradas todavía.")
        return

    nombres_cat = [c["nombre"] for c in categorias]
    cat_sel = st.selectbox("Categoría", nombres_cat, key="acc_categoria")
    cat_id = next(c["id"] for c in categorias if c["nombre"] == cat_sel)

    accesorios = (
        sb.table("accesorios")
        .select("id,descripcion,existencias")
        .eq("categoria_id", cat_id)
        .gt("existencias", 0)
        .order("descripcion")
        .execute()
        .data
    )

    if not accesorios:
        st.info(f"No hay existencias disponibles en {cat_sel}.")
        return

    etiquetas = [f'{a["descripcion"]} (disp: {a["existencias"]})' for a in accesorios]
    idx = st.selectbox("Producto disponible", range(len(etiquetas)), format_func=lambda i: etiquetas[i], key="acc_producto")
    accesorio = accesorios[idx]

    cantidad = st.number_input(
        "Cantidad", min_value=1, max_value=int(accesorio["existencias"]), value=1, key="acc_cantidad"
    )
    precio_unitario = _input_precio_unitario("acc")

    if st.button("➕ Agregar accesorio a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "accesorio",
            "accesorio_id": accesorio["id"],
            "descripcion": f'{cat_sel}: {accesorio["descripcion"]}',
            "cantidad": int(cantidad),
            "precio_unitario": precio_unitario,
        })
        st.success("Accesorio agregado")
        st.rerun()


def _mostrar_carrito():
    st.subheader("Artículos en esta venta")
    if not st.session_state.carrito:
        st.info("Aún no has agregado ningún artículo.")
        return

    for i, item in enumerate(st.session_state.carrito):
        col1, col2 = st.columns([5, 1])
        precio_txt = f' · ${item["precio_unitario"]:,.2f}' if item.get("precio_unitario") else ""
        col1.write(f'{item["descripcion"]} — cantidad: {item["cantidad"]}{precio_txt}')
        if col2.button("Quitar", key=f"quitar_{i}"):
            st.session_state.carrito.pop(i)
            st.rerun()


def mostrar_formulario_venta(sb):
    st.title("📝 Registro de venta")

    if "carrito" not in st.session_state:
        st.session_state.carrito = []

    tipo = st.radio("¿Qué quieres agregar?", ["Anteojos", "Lentes de contacto", "Accesorios"], horizontal=True)

    if tipo == "Anteojos":
        _seccion_anteojos(sb)
    elif tipo == "Lentes de contacto":
        _seccion_lentes_contacto(sb)
    elif tipo == "Accesorios":
        _seccion_accesorios(sb)

    st.divider()
    _mostrar_carrito()
    st.divider()

    st.subheader("Datos de la venta")

    folio = st.text_input("Folio de la nota de venta *")

    responsables = _cargar_responsables(sb)
    opciones_resp = [r["nombre"] for r in responsables] + ["Otro"]
    resp_sel = st.selectbox("Atendido por *", opciones_resp)

    responsable_id = None
    responsable_otro = None
    if resp_sel == "Otro":
        responsable_otro = st.text_input("Nombre de quien atendió *")
    else:
        responsable_id = next(r["id"] for r in responsables if r["nombre"] == resp_sel)

    total = st.number_input("Total de la venta ($) *", min_value=0.0, step=0.5, format="%.2f")
    if total > 0:
        st.caption(f"Total: ${total:,.2f}")

    if st.button("💾 Guardar venta", type="primary"):
        errores = []
        if not folio.strip():
            errores.append("Falta el folio.")
        if not st.session_state.carrito:
            errores.append("Agrega al menos un artículo a la venta.")
        if resp_sel == "Otro" and not (responsable_otro and responsable_otro.strip()):
            errores.append("Falta el nombre de quien atendió.")
        if total <= 0:
            errores.append("El total debe ser mayor a cero.")

        if errores:
            for e in errores:
                st.error(e)
            return

        try:
            venta = sb.table("ventas").insert({
                "folio": folio.strip(),
                "responsable_id": responsable_id,
                "responsable_otro": responsable_otro.strip() if responsable_otro else None,
                "total": float(total),
            }).execute()

            venta_id = venta.data[0]["id"]

            for item in st.session_state.carrito:
                detalle = {
                    "venta_id": venta_id,
                    "tipo_articulo": item["tipo_articulo"],
                    "cantidad": item["cantidad"],
                    "precio_unitario": item.get("precio_unitario"),
                }
                if item["tipo_articulo"] == "armazon":
                    detalle["armazon_id"] = item["armazon_id"]
                elif item["tipo_articulo"] == "lente_contacto":
                    detalle["lente_contacto_id"] = item["lente_contacto_id"]
                elif item["tipo_articulo"] == "accesorio":
                    detalle["accesorio_id"] = item["accesorio_id"]
                elif item["tipo_articulo"] == "mica":
                    detalle["mica_id"] = item["mica_id"]

                sb.table("venta_detalle").insert(detalle).execute()

            st.session_state.carrito = []
            st.success(f"✅ Venta folio {folio.strip()} guardada correctamente.")
            st.rerun()

        except Exception as e:
            st.error(f"Ocurrió un error al guardar la venta: {e}")
            st.warning(
                "Si el error menciona 'existencias suficientes', significa que alguien más "
                "vendió esa pieza mientras armabas esta venta. Revisa el carrito y ajusta."
            )
