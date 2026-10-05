# crud_periodos.py
# Cálculo del Impuesto a las Actividades Económicas + administración de períodos
import json
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

import conexion

db = conexion.Conexion()        # igual que en crud_clientes.py

D2 = Decimal("0.01")
D6 = Decimal("0.000001")
FORMULA_VERSION = "bloques_ceil_v1"


class ErrorImpuesto(Exception):
    """Errores de negocio con el mensaje exacto del documento."""


# ---------------------------------------------------------------
# 1) FUNCIONES PURAS (se pueden probar sin base de datos)
# ---------------------------------------------------------------
def a_decimal(valor):
    try:
        return Decimal(str(valor))
    except Exception:
        raise ErrorImpuesto("Ingrese un balance mayor que cero.")


def a_fecha(valor):
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ErrorImpuesto("La fecha Hasta debe ser posterior a la fecha Desde.")


def seleccionar_tarifa(tarifas, balance):
    """RF 10, 11, 12: TarifaDesde <= Balance <= TarifaHasta, una sola tarifa."""
    candidatas = [t for t in tarifas
                  if a_decimal(t["monto_desde"]) <= balance <= a_decimal(t["monto_hasta"])]
    if not candidatas:
        raise ErrorImpuesto("No existe una tarifa configurada para el balance indicado.")
    if len(candidatas) > 1:
        raise ErrorImpuesto("Existe más de una tarifa aplicable. Corrija la tabla tarifaria.")
    return candidatas[0]


def calcular_impuesto(balance, tarifa):
    """Sección 10 del documento. Devuelve precio (6 dec) y el detalle."""
    desde = a_decimal(tarifa["monto_desde"])
    base = a_decimal(tarifa["precio_base"])
    adicional = a_decimal(tarifa["adicional"])
    porcentaje = a_decimal(tarifa["porcentaje"])

    if porcentaje > 0:                                   # 10.4 tarifa porcentual
        precio = balance * porcentaje / Decimal(100)
        excedente = bloques = None
    else:                                                # 10.1 por bloques
        excedente = balance - desde
        bloques = (excedente / Decimal(1000)).to_integral_value(rounding=ROUND_CEILING)
        precio = base + bloques * adicional

    precio = precio.quantize(D6, rounding=ROUND_HALF_UP)
    return {
        "balance": str(balance),
        "rango": f"{desde} a {tarifa['monto_hasta']}",
        "precio_base": str(base),
        "excedente": None if excedente is None else str(excedente),
        "bloques": None if bloques is None else int(bloques),
        "adicional": str(adicional),
        "porcentaje": str(porcentaje),
        "precio": precio,
        "precio_mostrado": str(precio.quantize(D2, rounding=ROUND_HALF_UP)),
        "formula_version": FORMULA_VERSION,
    }


def meses_aplicables(p_desde, p_hasta, c_desde, c_hasta):
    """Meses de un cobro que caen dentro de la vigencia del período [desde, hasta)."""
    ini, fin = max(p_desde, c_desde), min(p_hasta, c_hasta)
    if ini >= fin:
        return 0
    return (fin.year - ini.year) * 12 + (fin.month - ini.month)


def cargo_periodo(cantidad, precio_mensual, meses):
    """Cargo del período = Cantidad x Precio mensual x Meses aplicables."""
    return (a_decimal(cantidad) * a_decimal(precio_mensual) * meses).quantize(D2, ROUND_HALF_UP)


# ---------------------------------------------------------------
# 2) CLASE CRUD (mismo estilo que crud_clientes)
#    Necesita db.consultar_dict(sql, valores) -> lista de diccionarios
# ---------------------------------------------------------------
class crud_periodos:

    def _tarifas_vigentes(self, producto, fecha):
        sql = """
            SELECT * FROM tarifas_impuesto
            WHERE codigo_producto=%s AND vigente_desde<=%s
              AND (vigente_hasta IS NULL OR %s<vigente_hasta)
        """
        return db.consultar_dict(sql, (producto, fecha, fecha))

    def _validar(self, datos, ignorar_id=0):
        """Devuelve (balance, desde, hasta, advertencias)."""
        if not datos.get("idCliente"):
            raise ErrorImpuesto("Seleccione un cliente.")
        if datos.get("codigo_producto") not in ("11801", "11802"):
            raise ErrorImpuesto("Confirme si la actividad corresponde a comercio o industria.")

        cli = db.consultar_dict("SELECT * FROM clientes WHERE idCliente=%s", (datos["idCliente"],))
        if not cli:
            raise ErrorImpuesto("Cliente no encontrado.")
        # AJUSTA 'tipo' al nombre real de tu columna que distingue empresa/persona
        if str(cli[0].get("tipo", "")).lower() != "empresa":
            raise ErrorImpuesto("El Impuesto a las Actividades Económicas requiere un cliente de tipo empresa.")

        balance = a_decimal(datos.get("monto"))
        if balance <= 0:
            raise ErrorImpuesto("Ingrese un balance mayor que cero.")

        desde, hasta = a_fecha(datos["desde"]), a_fecha(datos["hasta"])
        if desde >= hasta:
            raise ErrorImpuesto("La fecha Hasta debe ser posterior a la fecha Desde.")

        # RF 04: no superponer  ([desde,hasta) contra existentes)
        choque = db.consultar_dict("""
            SELECT idPeriodo FROM periodos_impuesto
            WHERE idCliente=%s AND codigo_producto=%s AND desde<%s AND hasta>%s
              AND idPeriodo<>%s
        """, (datos["idCliente"], datos["codigo_producto"], hasta, desde, ignorar_id))
        if choque:
            raise ErrorImpuesto("El período indicado se superpone con un período existente.")

        # RF 06: advertir huecos
        avisos = []
        prev = db.consultar_dict("""
            SELECT MAX(hasta) AS ultimo FROM periodos_impuesto
            WHERE idCliente=%s AND codigo_producto=%s AND hasta<=%s
        """, (datos["idCliente"], datos["codigo_producto"], desde))
        if prev and prev[0]["ultimo"] and prev[0]["ultimo"] < desde:
            avisos.append(f"Hay un espacio sin cobertura entre {prev[0]['ultimo']} y {desde}.")
        return balance, desde, hasta, avisos

    def previsualizar(self, datos):
        """RF 17/18: calcula y muestra el detalle SIN guardar."""
        balance, desde, hasta, avisos = self._validar(datos)
        tarifa = seleccionar_tarifa(self._tarifas_vigentes(datos["codigo_producto"], desde), balance)
        r = calcular_impuesto(balance, tarifa)
        r["idTarifa"] = tarifa["idTarifa"]
        r["precio"] = str(r["precio"])
        r["avisos"] = avisos
        return r

    MSG_FACT = "El período ya fue utilizado en recibos y no puede recalcularse automáticamente."
    SQL_INS = """
        INSERT INTO periodos_impuesto
        (idCliente,codigo_producto,desde,hasta,monto,cantidad,precio,subtotal,
         idTarifa,formula_version,detalle_calculo,usuario)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    SQL_BIT = """
        INSERT INTO bitacora_periodos
        (idPeriodo,accion,monto_anterior,monto_nuevo,precio_anterior,precio_nuevo,motivo,autorizado_por,usuario)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    def _preparar(self, datos, ignorar_id=0):
        balance, desde, hasta, avisos = self._validar(datos, ignorar_id)
        tarifa = seleccionar_tarifa(self._tarifas_vigentes(datos["codigo_producto"], desde), balance)
        r = calcular_impuesto(balance, tarifa)
        cantidad = a_decimal(datos.get("cantidad", "1.00"))
        subtotal = (cantidad * r["precio"]).quantize(D2, ROUND_HALF_UP)
        detalle = {k: v for k, v in r.items() if k != "precio"}
        valores = (datos["idCliente"], datos["codigo_producto"], desde, hasta, balance, cantidad,
                   r["precio"], subtotal, tarifa["idTarifa"], FORMULA_VERSION,
                   json.dumps(detalle), datos.get("usuario") or "sin usuario")
        return valores, r, avisos

    def administrar(self, datos):
        try:
            accion = datos.get("accion")
            if accion == "previsualizar":
                return {"ok": True, "detalle": self.previsualizar(datos)}

            if accion == "nuevo":
                valores, r, avisos = self._preparar(datos)
                res = db.ejecutar(self.SQL_INS, valores)
                if res != "ok":
                    return {"ok": False, "mensaje": f"No se pudo guardar el período. {res}"}
                return {"ok": True, "mensaje": "Período guardado", "avisos": avisos,
                        "precio": r["precio_mostrado"]}

            if accion == "cambio_balance":          # RF 07: cierra el vigente y crea uno nuevo
                desde = a_fecha(datos["desde"])
                vig = db.consultar_dict("""
                    SELECT * FROM periodos_impuesto
                    WHERE idCliente=%s AND codigo_producto=%s AND desde<%s AND hasta>%s
                """, (datos["idCliente"], datos["codigo_producto"], desde, desde))
                if not vig:
                    raise ErrorImpuesto("No hay un período vigente que cerrar en esa fecha. Use Guardar período.")
                vig = vig[0]
                if vig["facturado"]:
                    raise ErrorImpuesto(self.MSG_FACT)
                valores, r, avisos = self._preparar(datos, vig["idPeriodo"])
                usuario = datos.get("usuario") or "sin usuario"
                res = db.ejecutar_varios([
                    ("UPDATE periodos_impuesto SET hasta=%s WHERE idPeriodo=%s", (desde, vig["idPeriodo"])),
                    (self.SQL_INS, valores),
                    (self.SQL_BIT, (vig["idPeriodo"], "cierre_por_cambio", vig["monto"], valores[4],
                                    vig["precio"], r["precio"], "Cambio de balance", None, usuario)),
                ])
                if res != "ok":
                    return {"ok": False, "mensaje": f"No se pudo guardar el cambio. {res}"}
                return {"ok": True, "mensaje": "Período anterior cerrado y nuevo período creado",
                        "avisos": avisos, "precio": r["precio_mostrado"]}

            if accion == "recalcular":              # RF 09, 14, 16
                motivo = (datos.get("motivo") or "").strip()
                if not motivo:
                    raise ErrorImpuesto("Indique el motivo del recálculo.")
                p = db.consultar_dict("SELECT * FROM periodos_impuesto WHERE idPeriodo=%s", (datos["idPeriodo"],))
                if not p:
                    raise ErrorImpuesto("Período no encontrado.")
                p = p[0]
                aut = (datos.get("autorizado_por") or "").strip()
                if p["facturado"] and not aut:
                    raise ErrorImpuesto(self.MSG_FACT)
                balance = a_decimal(datos.get("monto") or p["monto"])
                if balance <= 0:
                    raise ErrorImpuesto("Ingrese un balance mayor que cero.")
                tarifa = seleccionar_tarifa(self._tarifas_vigentes(p["codigo_producto"], p["desde"]), balance)
                r = calcular_impuesto(balance, tarifa)
                subtotal = (a_decimal(p["cantidad"]) * r["precio"]).quantize(D2, ROUND_HALF_UP)
                usuario = datos.get("usuario") or "sin usuario"
                detalle = {k: v for k, v in r.items() if k != "precio"}
                res = db.ejecutar_varios([
                    ("""UPDATE periodos_impuesto SET monto=%s,precio=%s,subtotal=%s,idTarifa=%s,
                        formula_version=%s,detalle_calculo=%s,usuario=%s,fecha_calculo=NOW()
                        WHERE idPeriodo=%s""",
                     (balance, r["precio"], subtotal, tarifa["idTarifa"], FORMULA_VERSION,
                      json.dumps(detalle), usuario, p["idPeriodo"])),
                    (self.SQL_BIT, (p["idPeriodo"], "correccion_autorizada" if p["facturado"] else "recalculo",
                                    p["monto"], balance, p["precio"], r["precio"], motivo, aut or None, usuario)),
                ])
                if res != "ok":
                    return {"ok": False, "mensaje": f"No se pudo recalcular. {res}"}
                return {"ok": True, "mensaje": "Período recalculado y registrado en bitácora",
                        "precio": r["precio_mostrado"]}

            if accion == "cobro":                   # sección 15: integración con el cobro
                c_desde, c_hasta = a_fecha(datos["cobro_desde"]), a_fecha(datos["cobro_hasta"])
                if c_desde >= c_hasta:
                    raise ErrorImpuesto("La fecha Hasta debe ser posterior a la fecha Desde.")
                filas = db.consultar_dict("""
                    SELECT * FROM periodos_impuesto
                    WHERE idCliente=%s AND codigo_producto=%s AND desde<%s AND hasta>%s ORDER BY desde
                """, (datos["idCliente"], datos["codigo_producto"], c_hasta, c_desde))
                detalle, total, meses_tot = [], Decimal(0), 0
                for f in filas:
                    m = meses_aplicables(f["desde"], f["hasta"], c_desde, c_hasta)
                    cargo = cargo_periodo(f["cantidad"], f["precio"], m)
                    total += cargo
                    meses_tot += m
                    detalle.append({"desde": str(f["desde"]), "hasta": str(f["hasta"]), "meses": m,
                                    "precio": str(a_decimal(f["precio"]).quantize(D2)), "cargo": str(cargo)})
                meses_cobro = (c_hasta.year - c_desde.year) * 12 + c_hasta.month - c_desde.month
                aviso = "Hay meses del cobro sin período definido." if meses_tot < meses_cobro else ""
                return {"ok": True, "detalle": detalle, "total": str(total.quantize(D2)), "aviso": aviso}

            if accion == "listar":
                filas = db.consultar_dict("""
                    SELECT idPeriodo,desde,hasta,monto,codigo_producto,precio,facturado
                    FROM periodos_impuesto WHERE idCliente=%s AND codigo_producto=%s
                    ORDER BY desde
                """, (datos["idCliente"], datos["codigo_producto"]))
                hoy, vigente, salida = date.today(), None, []
                for f in filas:
                    est = "Histórico" if f["hasta"] <= hoy else ("Vigente" if f["desde"] <= hoy else "Futuro")
                    if est == "Vigente":
                        vigente = str(a_decimal(f["precio"]).quantize(D2))
                    salida.append({**{k: str(v) for k, v in f.items()}, "estado": est})
                total = str(sum((a_decimal(f["precio"]) for f in filas), Decimal(0)).quantize(D2))
                return {"ok": True, "periodos": salida, "total_referencial": total, "mensual_vigente": vigente}

            return {"ok": False, "mensaje": "Acción no válida"}
        except ErrorImpuesto as e:
            return {"ok": False, "mensaje": str(e)}
        except Exception as e:
            return {"ok": False, "mensaje": f"Error en el período: {e}"}