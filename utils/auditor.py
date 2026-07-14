"""
Auditor: reportes de ventas por periodo.

Muestra un resumen general ($ total y # de folios), un resumen por
categoría (armazones por rango, lentes de contacto, micas, accesorios
por categoría), detalle drill-down por folio/responsable/fecha/total,
y un desglose por responsable (folios, totales y mercancía vendida).
Exportable a Excel y PDF con selección de qué secciones incluir.
"""

import io
import os
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st
from fpdf import FPDF

MEXICO_TZ = pytz.timezone("America/Mexico_City")


def _rango_fechas():
    opcion = st.radio("Periodo", ["Esta semana", "Este mes", "Personalizado"], horizontal=True)
    hoy = datetime.now(MEXICO_TZ).date()

    if opcion == "Esta semana":
        inicio = hoy - timedelta(days=hoy.weekday())
        fin = hoy
    elif opcion == "Este mes":
        inicio = hoy.replace(day=1)
        fin = hoy
    else:
        col1, col2 = st.columns(2)
        inicio = col1.date_input("Desde", value=hoy.replace(day=1))
        fin = col2.date_input("Hasta", value=hoy)

    return inicio, fin


def _limites_utc(inicio, fin):
    inicio_dt = MEXICO_TZ.localize(datetime.combine(inicio, datetime.min.time()))
    fin_dt = MEXICO_TZ.localize(datetime.combine(fin, datetime.max.time()))
    return inicio_dt.astimezone(pytz.UTC).isoformat(), fin_dt.astimezone(pytz.UTC).isoformat()


def _formatear_fecha(fecha_iso):
    dt = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
    return dt.astimezone(MEXICO_TZ).strftime("%d/%m/%Y %H:%M")


def _clasificar(item):
    tipo = item["tipo_articulo"]
    if tipo == "armazon":
        rango = item["armazones"]["tipo"] if item.get("armazones") else None
        etiquetas = {"marca": "Armazones de marca", "linea": "Armazones de línea", "basico": "Armazones básicos"}
        return etiquetas.get(rango, "Armazones (sin clasificar)")
    elif tipo == "lente_contacto":
        return "Lentes de contacto"
    elif tipo == "mica":
        return "Micas"
    elif tipo == "accesorio":
        cat = None
        if item.get("accesorios") and item["accesorios"].get("categorias_accesorios"):
            cat = item["accesorios"]["categorias_accesorios"]["nombre"]
        return f"Accesorios: {cat or 'Sin categoría'}"
    return "Otro"


def _descripcion_articulo(item):
    tipo = item["tipo_articulo"]
    if tipo == "armazon" and item.get("armazones"):
        marca = item["armazones"]["marcas"]["nombre"] if item["armazones"].get("marcas") else ""
        return f'{marca} {item["armazones"]["codigo"]}'.strip()
    if tipo == "lente_contacto" and item.get("lentes_contacto"):
        marca = item["lentes_contacto"]["marcas_lc"]["nombre"] if item["lentes_contacto"].get("marcas_lc") else ""
        return f'{marca} {item["lentes_contacto"]["diseno"]}'.strip()
    if tipo == "mica" and item.get("micas"):
        return item["micas"]["nombre"]
    if tipo == "accesorio" and item.get("accesorios"):
        return item["accesorios"]["descripcion"]
    return "—"


def _nombre_responsable(venta):
    if venta.get("responsables"):
        return venta["responsables"]["nombre"]
    return venta.get("responsable_otro") or "—"


def _tipo_legible(tipo):
    return {
        "armazon": "Armazón",
        "accesorio": "Accesorio",
        "lente_contacto": "Lente de contacto",
        "mica": "Mica",
    }.get(tipo, tipo)


def _marca_de(item):
    tipo = item["tipo_articulo"]
    if tipo == "armazon" and item.get("armazones") and item["armazones"].get("marcas"):
        return item["armazones"]["marcas"]["nombre"]
    if tipo == "lente_contacto" and item.get("lentes_contacto") and item["lentes_contacto"].get("marcas_lc"):
        return item["lentes_contacto"]["marcas_lc"]["nombre"]
    return None


def _proveedor_de(item):
    tipo = item["tipo_articulo"]
    tabla = {"armazon": "armazones", "accesorio": "accesorios", "lente_contacto": "lentes_contacto"}.get(tipo)
    if tabla and item.get(tabla) and item[tabla].get("proveedores"):
        return item[tabla]["proveedores"]["nombre"]
    return None


def _generar_excel(secciones: dict):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre_hoja, df in secciones.items():
            df.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)
    return buffer.getvalue()


def _generar_pdf(inicio, fin, total_dinero, num_folios, secciones: dict):
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=10, y=8, w=27)
        pdf.set_xy(42, 10)
    else:
        pdf.set_xy(10, 10)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Centro Ocular Alameda", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(42 if os.path.exists("assets/logo.png") else 10)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Reporte de Auditoria", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(38)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Periodo: {inicio} a {fin}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Total vendido: ${total_dinero:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Numero de folios: {num_folios}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for titulo, df in secciones.items():
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, titulo.encode("latin-1", "replace").decode("latin-1"), new_x="LMARGIN", new_y="NEXT")

        if df.empty:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, "Sin datos.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            continue

        columnas = list(df.columns)
        ancho_col = 190 / len(columnas)

        pdf.set_font("Helvetica", "B", 9)
        for col in columnas:
            texto = str(col).encode("latin-1", "replace").decode("latin-1")
            pdf.cell(ancho_col, 7, texto, border=1)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for _, fila in df.iterrows():
            if pdf.get_y() > 270:
                pdf.add_page()
            for col in columnas:
                texto = str(fila[col]).encode("latin-1", "replace").decode("latin-1")
                if len(texto) > 28:
                    texto = texto[:25] + "..."
                pdf.cell(ancho_col, 7, texto, border=1)
            pdf.ln()
        pdf.ln(4)

    return bytes(pdf.output())


def mostrar_auditor(sb):
    st.title("📊 Auditor")

    inicio, fin = _rango_fechas()
    if inicio > fin:
        st.error("La fecha 'Desde' no puede ser posterior a 'Hasta'.")
        return

    inicio_utc, fin_utc = _limites_utc(inicio, fin)

    ventas = (
        sb.table("ventas")
        .select("id,folio,fecha,total,responsable_otro,responsables(nombre)")
        .gte("fecha", inicio_utc)
        .lte("fecha", fin_utc)
        .eq("cancelada", False)
        .order("fecha")
        .execute()
        .data
    )

    if not ventas:
        st.info("No hay ventas registradas en este periodo.")
        return

    venta_por_id = {v["id"]: v for v in ventas}
    venta_ids = list(venta_por_id.keys())

    detalle = (
        sb.table("venta_detalle")
        .select(
            "id,venta_id,tipo_articulo,cantidad,precio_unitario,"
            "armazones(tipo,codigo,marcas(nombre),proveedores(nombre)),"
            "accesorios(descripcion,categorias_accesorios(nombre),proveedores(nombre)),"
            "lentes_contacto(diseno,marcas_lc(nombre),proveedores(nombre)),"
            "micas(nombre)"
        )
        .in_("venta_id", venta_ids)
        .execute()
        .data
    )

    total_dinero = sum(v["total"] for v in ventas)
    col1, col2 = st.columns(2)
    col1.metric("Ventas totales", f"${total_dinero:,.2f}")
    col2.metric("Número de folios", len(ventas))

    # ---------- Resumen por categoría ----------
    resumen = {}
    for item in detalle:
        cat = _clasificar(item)
        resumen.setdefault(cat, {"piezas": 0, "items": []})
        resumen[cat]["piezas"] += item["cantidad"]
        resumen[cat]["items"].append(item)

    st.subheader("Resumen por categoría")
    df_resumen = pd.DataFrame(
        [{"Categoría": k, "Piezas vendidas": v["piezas"]} for k, v in sorted(resumen.items())]
    )
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    st.subheader("Detalle por categoría")
    categoria_sel = st.selectbox("Selecciona una categoría para ver el detalle", sorted(resumen.keys()))

    filas_detalle_cat = []
    for item in resumen[categoria_sel]["items"]:
        venta = venta_por_id[item["venta_id"]]
        filas_detalle_cat.append({
            "Folio": venta["folio"],
            "Fecha": _formatear_fecha(venta["fecha"]),
            "Responsable": _nombre_responsable(venta),
            "Artículo": _descripcion_articulo(item),
            "Cantidad": item["cantidad"],
            "Precio unitario": f'${item["precio_unitario"]:,.2f}' if item.get("precio_unitario") else "—",
            "Total del folio": f'${venta["total"]:,.2f}',
        })
    df_detalle_categoria = pd.DataFrame(filas_detalle_cat)
    st.dataframe(df_detalle_categoria, use_container_width=True, hide_index=True)

    # ---------- Detalle completo (para exportar) ----------
    filas_detalle_completo = []
    for item in detalle:
        venta = venta_por_id[item["venta_id"]]
        filas_detalle_completo.append({
            "Folio": venta["folio"],
            "Fecha": _formatear_fecha(venta["fecha"]),
            "Responsable": _nombre_responsable(venta),
            "Categoría": _clasificar(item),
            "Artículo": _descripcion_articulo(item),
            "Cantidad": item["cantidad"],
            "Precio unitario": item.get("precio_unitario") or "",
            "Total del folio": venta["total"],
        })
    df_detalle_completo = pd.DataFrame(filas_detalle_completo)

    # ---------- Ventas por responsable ----------
    st.subheader("Ventas por responsable")

    por_responsable = {}
    for v in ventas:
        nombre = _nombre_responsable(v)
        por_responsable.setdefault(nombre, {"folios": [], "total": 0.0})
        por_responsable[nombre]["folios"].append(v)
        por_responsable[nombre]["total"] += v["total"]

    df_resumen_responsable = pd.DataFrame([
        {"Responsable": nombre, "Folios vendidos": len(datos["folios"]), "Total vendido": f'${datos["total"]:,.2f}'}
        for nombre, datos in sorted(por_responsable.items(), key=lambda x: -x[1]["total"])
    ])
    st.dataframe(df_resumen_responsable, use_container_width=True, hide_index=True)

    responsable_sel = st.selectbox("Ver detalle de responsable", sorted(por_responsable.keys()))
    filas_resp = []
    for v in por_responsable[responsable_sel]["folios"]:
        items_venta = [it for it in detalle if it["venta_id"] == v["id"]]
        mercancia = ", ".join(_descripcion_articulo(it) for it in items_venta) or "—"
        filas_resp.append({
            "Folio": v["folio"],
            "Fecha": _formatear_fecha(v["fecha"]),
            "Mercancía": mercancia,
            "Total": f'${v["total"]:,.2f}',
        })
    df_detalle_responsable = pd.DataFrame(filas_resp)
    st.dataframe(df_detalle_responsable, use_container_width=True, hide_index=True)

    # Tabla completa por responsable, para exportar (todos los responsables, no solo el seleccionado)
    filas_resp_export = []
    for nombre, datos in por_responsable.items():
        for v in datos["folios"]:
            items_venta = [it for it in detalle if it["venta_id"] == v["id"]]
            mercancia = ", ".join(_descripcion_articulo(it) for it in items_venta) or "—"
            filas_resp_export.append({
                "Responsable": nombre,
                "Folio": v["folio"],
                "Fecha": _formatear_fecha(v["fecha"]),
                "Mercancía": mercancia,
                "Total": v["total"],
            })
    df_responsable_export = pd.DataFrame(filas_resp_export)

    # ---------- Explorador de ventas (filtros combinables tipo Excel) ----------
    st.subheader("🔍 Explorador de ventas")
    st.caption(
        "Filtra por cualquier combinación de responsable, tipo de artículo, categoría, "
        "marca o proveedor. Los filtros se combinan entre sí (Y lógico)."
    )

    filas_explorador = []
    for item in detalle:
        venta = venta_por_id[item["venta_id"]]
        filas_explorador.append({
            "Folio": venta["folio"],
            "Fecha": _formatear_fecha(venta["fecha"]),
            "Responsable": _nombre_responsable(venta),
            "Tipo": _tipo_legible(item["tipo_articulo"]),
            "Categoría": _clasificar(item),
            "Marca": _marca_de(item) or "—",
            "Proveedor": _proveedor_de(item) or "—",
            "Artículo": _descripcion_articulo(item),
            "Cantidad": item["cantidad"],
            "Precio unitario": item.get("precio_unitario") or None,
            "Total del folio": venta["total"],
        })
    df_explorador_base = pd.DataFrame(filas_explorador)

    col1, col2, col3 = st.columns(3)
    f_responsable = col1.multiselect("Responsable", sorted(df_explorador_base["Responsable"].unique()))
    f_tipo = col2.multiselect("Tipo de artículo", sorted(df_explorador_base["Tipo"].unique()))
    f_categoria = col3.multiselect("Categoría", sorted(df_explorador_base["Categoría"].unique()))

    col4, col5 = st.columns(2)
    marcas_disponibles = sorted(m for m in df_explorador_base["Marca"].unique() if m != "—")
    proveedores_disponibles = sorted(p for p in df_explorador_base["Proveedor"].unique() if p != "—")
    f_marca = col4.multiselect("Marca", marcas_disponibles)
    f_proveedor = col5.multiselect("Proveedor", proveedores_disponibles)

    df_filtrado = df_explorador_base.copy()
    if f_responsable:
        df_filtrado = df_filtrado[df_filtrado["Responsable"].isin(f_responsable)]
    if f_tipo:
        df_filtrado = df_filtrado[df_filtrado["Tipo"].isin(f_tipo)]
    if f_categoria:
        df_filtrado = df_filtrado[df_filtrado["Categoría"].isin(f_categoria)]
    if f_marca:
        df_filtrado = df_filtrado[df_filtrado["Marca"].isin(f_marca)]
    if f_proveedor:
        df_filtrado = df_filtrado[df_filtrado["Proveedor"].isin(f_proveedor)]

    if df_filtrado.empty:
        st.warning("Ningún artículo coincide con esos filtros.")
    else:
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Folios encontrados", df_filtrado["Folio"].nunique())
        mcol2.metric("Piezas", int(df_filtrado["Cantidad"].sum()))
        mcol3.metric("Total (folios únicos)", f'${df_filtrado.drop_duplicates("Folio")["Total del folio"].sum():,.2f}')

        df_mostrar = df_filtrado.copy()
        df_mostrar["Precio unitario"] = df_mostrar["Precio unitario"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )
        df_mostrar["Total del folio"] = df_mostrar["Total del folio"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    st.divider()

    # ---------- Exportar ----------
    st.subheader("Exportar")

    opciones_contenido = st.multiselect(
        "¿Qué quieres incluir en el reporte?",
        ["Resumen por categoría", "Detalle completo", "Resumen por responsable",
         "Detalle por responsable", "Explorador (con filtros actuales)"],
        default=["Resumen por categoría", "Detalle completo", "Resumen por responsable", "Detalle por responsable"],
    )

    secciones = {}
    if "Resumen por categoría" in opciones_contenido:
        secciones["Resumen por categoría"] = df_resumen
    if "Detalle completo" in opciones_contenido:
        secciones["Detalle completo"] = df_detalle_completo
    if "Resumen por responsable" in opciones_contenido:
        secciones["Resumen por responsable"] = df_resumen_responsable
    if "Detalle por responsable" in opciones_contenido:
        secciones["Detalle por responsable"] = df_responsable_export
    if "Explorador (con filtros actuales)" in opciones_contenido and not df_filtrado.empty:
        secciones["Explorador filtrado"] = df_mostrar

    if not secciones:
        st.info("Selecciona al menos una sección para poder exportar.")
        return

    col1, col2 = st.columns(2)
    with col1:
        excel_bytes = _generar_excel(secciones)
        st.download_button(
            "📥 Descargar Excel",
            data=excel_bytes,
            file_name=f"reporte_coa_{inicio}_{fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col2:
        pdf_bytes = _generar_pdf(inicio, fin, total_dinero, len(ventas), secciones)
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"reporte_coa_{inicio}_{fin}.pdf",
            mime="application/pdf",
        )
