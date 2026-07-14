"""
Auditor: reportes de ventas por periodo.

Muestra un resumen general ($ total y # de folios), un resumen por
categoría (armazones por rango, lentes de contacto, micas, accesorios
por categoría), y un detalle drill-down por folio/responsable/fecha
para cualquier categoría seleccionada. Exportable a Excel y PDF.
"""

import io
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


def _generar_excel(df_resumen, df_detalle):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)
    return buffer.getvalue()


def _generar_pdf(df_resumen, inicio, fin, total_dinero, num_folios):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Centro Ocular Alameda - Reporte de Auditoria", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Periodo: {inicio} a {fin}", ln=True)
    pdf.cell(0, 8, f"Total vendido: ${total_dinero:,.2f}", ln=True)
    pdf.cell(0, 8, f"Numero de folios: {num_folios}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(140, 8, "Categoria", border=1)
    pdf.cell(40, 8, "Piezas", border=1, ln=True)

    pdf.set_font("Helvetica", "", 11)
    for _, row in df_resumen.iterrows():
        categoria = str(row["Categoría"]).encode("latin-1", "replace").decode("latin-1")
        pdf.cell(140, 8, categoria, border=1)
        pdf.cell(40, 8, str(row["Piezas vendidas"]), border=1, ln=True)

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
            "armazones(tipo,codigo,marcas(nombre)),"
            "accesorios(descripcion,categorias_accesorios(nombre)),"
            "lentes_contacto(diseno,marcas_lc(nombre)),"
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

    resumen = {}
    for item in detalle:
        cat = _clasificar(item)
        resumen.setdefault(cat, {"piezas": 0, "items": []})
        resumen[cat]["piezas"] += item["cantidad"]
        resumen[cat]["items"].append(item)

    st.subheader("Resumen por categoría")
    filas_resumen = [
        {"Categoría": k, "Piezas vendidas": v["piezas"]} for k, v in sorted(resumen.items())
    ]
    df_resumen = pd.DataFrame(filas_resumen)
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    st.subheader("Detalle por categoría")
    categoria_sel = st.selectbox("Selecciona una categoría para ver el detalle", sorted(resumen.keys()))

    filas_detalle = []
    for item in resumen[categoria_sel]["items"]:
        venta = venta_por_id[item["venta_id"]]
        responsable = venta["responsables"]["nombre"] if venta.get("responsables") else (venta.get("responsable_otro") or "—")
        filas_detalle.append({
            "Folio": venta["folio"],
            "Fecha": _formatear_fecha(venta["fecha"]),
            "Responsable": responsable,
            "Artículo": _descripcion_articulo(item),
            "Cantidad": item["cantidad"],
            "Precio unitario": f'${item["precio_unitario"]:,.2f}' if item.get("precio_unitario") else "—",
        })

    df_detalle_categoria = pd.DataFrame(filas_detalle)
    st.dataframe(df_detalle_categoria, use_container_width=True, hide_index=True)

    st.subheader("Exportar")

    filas_detalle_completo = []
    for item in detalle:
        venta = venta_por_id[item["venta_id"]]
        responsable = venta["responsables"]["nombre"] if venta.get("responsables") else (venta.get("responsable_otro") or "—")
        filas_detalle_completo.append({
            "Folio": venta["folio"],
            "Fecha": _formatear_fecha(venta["fecha"]),
            "Responsable": responsable,
            "Categoría": _clasificar(item),
            "Artículo": _descripcion_articulo(item),
            "Cantidad": item["cantidad"],
            "Precio unitario": item.get("precio_unitario") or "",
        })
    df_detalle_completo = pd.DataFrame(filas_detalle_completo)

    col1, col2 = st.columns(2)
    with col1:
        excel_bytes = _generar_excel(df_resumen, df_detalle_completo)
        st.download_button(
            "📥 Descargar Excel",
            data=excel_bytes,
            file_name=f"reporte_coa_{inicio}_{fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col2:
        pdf_bytes = _generar_pdf(df_resumen, inicio, fin, total_dinero, len(ventas))
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"reporte_coa_{inicio}_{fin}.pdf",
            mime="application/pdf",
        )
