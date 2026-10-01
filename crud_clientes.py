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

    def _validar(self, datos):
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
        """, (datos["idCliente"], datos["codigo_producto"], hasta, desde))
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

    def administrar(self, datos):
        try:
            accion = datos.get("accion")
            if accion == "previsualizar":
                return {"ok": True, "detalle": self.previsualizar(datos)}

            if accion == "nuevo":
                balance, desde, hasta, avisos = self._validar(datos)
                tarifa = seleccionar_tarifa(self._tarifas_vigentes(datos["codigo_producto"], desde), balance)
                r = calcular_impuesto(balance, tarifa)
                cantidad = a_decimal(datos.get("cantidad", "1.00"))
                subtotal = (cantidad * r["precio"]).quantize(D2, ROUND_HALF_UP)
                detalle = {k: v for k, v in r.items() if k != "precio"}
                sql = """
                    INSERT INTO periodos_impuesto
                    (idCliente,codigo_producto,desde,hasta,monto,cantidad,precio,subtotal,
                     idTarifa,formula_version,detalle_calculo,usuario)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                valores = (datos["idCliente"], datos["codigo_producto"], desde, hasta, balance,
                           cantidad, r["precio"], subtotal, tarifa["idTarifa"],
                           FORMULA_VERSION, json.dumps(detalle), datos.get("usuario", "sistema"))
                db.ejecutar(sql, valores)
                return {"ok": True, "mensaje": "Período guardado", "avisos": avisos,
                        "precio": r["precio_mostrado"]}

            if accion == "listar":
                filas = db.consultar_dict("""
                    SELECT idPeriodo,desde,hasta,monto,codigo_producto,precio,facturado
                    FROM periodos_impuesto WHERE idCliente=%s AND codigo_producto=%s
                    ORDER BY desde
                """, (datos["idCliente"], datos["codigo_producto"]))
                total = str(sum((a_decimal(f["precio"]) for f in filas), Decimal(0)).quantize(D2))
                filas = [{k: str(v) for k, v in f.items()} for f in filas]  # JSON seguro
                return {"ok": True, "periodos": filas, "total_referencial": total}

            return {"ok": False, "mensaje": "Acción no válida"}
        except ErrorImpuesto as e:
            return {"ok": False, "mensaje": str(e)}
        except Exception as e:
            return {"ok": False, "mensaje": f"Error al guardar el período: {e}"}