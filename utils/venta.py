"""
Formulario de registro de venta (rol: ventas / Andrea).

Flujo:
1. Andrea va agregando artículos a un "carrito" temporal (armazones,
   lentes de contacto o accesorios), eligiendo siempre de listas
   desplegables que solo muestran lo que hay en existencia.
2. Al final llena folio, responsable y total, y guarda todo el folio
   de un jalón. Cada artículo del carrito se inserta en venta_detalle,
   y el trigger de la base de datos descuenta el inventario solo.
"""

import streamlit as st


def _cargar_marcas(sb):
    return sb.table("marcas").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_responsables(sb):
    return sb.table("responsables").select("id,nombre").eq("activo", True).order("nombre").execute().data


def _cargar_categorias_accesorios(sb):
    return sb.table("categorias_accesorios").select("id,nombre").eq("activo", True).order("nombre").execute().data


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

    if st.button("➕ Agregar armazón a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "armazon",
            "armazon_id": armazon["id"],
            "descripcion": f'Armazón {marca_sel} {armazon["codigo"]}',
            "cantidad": int(cantidad),
        })
        st.success("Armazón agregado")
        st.rerun()


def _seccion_lentes_contacto(sb):
    st.subheader("Agregar lentes de contacto")
    marcas = _cargar_marcas(sb)
    if not marcas:
        st.warning("No hay marcas registradas todavía.")
        return

    nombres_marca = [m["nombre"] for m in marcas]
    marca_sel = st.selectbox("Marca", nombres_marca, key="lc_marca")
    marca_id = next(m["id"] for m in marcas if m["nombre"] == marca_sel)

    lentes = (
        sb.table("lentes_contacto")
        .select("id,diseno,existencias")
        .eq("marca_id", marca_id)
        .gt("existencias", 0)
        .order("diseno")
        .execute()
        .data
    )

    if not lentes:
        st.info(f"No hay existencias disponibles de {marca_sel}.")
        return

    etiquetas = [f'{l["diseno"]} (disp: {l["existencias"]})' for l in lentes]
    idx = st.selectbox("Diseño disponible", range(len(etiquetas)), format_func=lambda i: etiquetas[i], key="lc_diseno")
    lente = lentes[idx]

    cantidad = st.number_input(
        "Cantidad", min_value=1, max_value=int(lente["existencias"]), value=1, key="lc_cantidad"
    )

    if st.button("➕ Agregar lentes de contacto a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "lente_contacto",
            "lente_contacto_id": lente["id"],
            "descripcion": f'Lentes de contacto {marca_sel} {lente["diseno"]}',
            "cantidad": int(cantidad),
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

    if st.button("➕ Agregar accesorio a la venta"):
        st.session_state.carrito.append({
            "tipo_articulo": "accesorio",
            "accesorio_id": accesorio["id"],
            "descripcion": f'{cat_sel}: {accesorio["descripcion"]}',
            "cantidad": int(cantidad),
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
        col1.write(f'{item["descripcion"]} — cantidad: {item["cantidad"]}')
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
                }
                if item["tipo_articulo"] == "armazon":
                    detalle["armazon_id"] = item["armazon_id"]
                elif item["tipo_articulo"] == "lente_contacto":
                    detalle["lente_contacto_id"] = item["lente_contacto_id"]
                elif item["tipo_articulo"] == "accesorio":
                    detalle["accesorio_id"] = item["accesorio_id"]

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
