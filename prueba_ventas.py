"""Pruebas del flujo de ventas y del CRUD de clientes.

Cubre los 8 casos de uso documentados en docs/clientes-y-ventas-diseno.md,
incluidos los casos que DEBEN fallar.

Crea sus propios datos (un producto y un cliente de prueba) para no depender
de lo que haya cargado, y los deja desactivados al terminar.

Uso:  python prueba_ventas.py
"""

import re
from decimal import Decimal

from erp import crear_app
from erp.extensiones import db
from erp.modelos import Cliente, MovimientoStock, Producto, Venta

CODIGO_PRUEBA = "TEST-VENTAS"
CLIENTE_PRUEBA = "Cliente de prueba automatizada"
STOCK_INICIAL = Decimal("50")
PRECIO = Decimal("1000.00")


def ok(numero, texto):
    print(f"  {numero:>2}. {texto}")


def csrf(cliente, ruta):
    """Extrae el token CSRF de un formulario."""
    html = cliente.get(ruta).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def aviso(html, clase="error"):
    """Devuelve el texto del mensaje flash, o None."""
    encontrado = re.search(rf'aviso--{clase}">([^<]+)', html)
    return encontrado.group(1).strip() if encontrado else None


# Clientes que crea la prueba y que hay que limpiar entre corridas.
CLIENTES_DE_PRUEBA = (
    "Ferretería Industrial del Norte", "Otro nombre", "Sin documento A",
    "Sin documento B", "Cliente creado desde la venta",
    "Control de destino externo",
)
DOCUMENTO_DE_PRUEBA = "30-12345678-9"


def preparar(app):
    """Deja el producto y el cliente de prueba en un estado conocido.

    Limpia también lo que haya quedado de corridas anteriores. No alcanza con
    desactivar los clientes: el documento es ÚNICO en la base, así que si no se
    libera, la segunda corrida choca contra el de la primera.
    """
    with app.app_context():
        for razon in CLIENTES_DE_PRUEBA:
            for anterior in db.session.query(Cliente).filter_by(razon_social=razon).all():
                anterior.documento = None
                anterior.activo = False

        for anterior in db.session.query(Cliente).filter_by(documento=DOCUMENTO_DE_PRUEBA).all():
            anterior.documento = None
            anterior.activo = False

        db.session.commit()
        producto = db.session.query(Producto).filter_by(codigo=CODIGO_PRUEBA).first()
        if producto is None:
            producto = Producto(codigo=CODIGO_PRUEBA, nombre="Producto de prueba")
            db.session.add(producto)
        producto.precio = PRECIO
        producto.stock = STOCK_INICIAL
        producto.stock_minimo = Decimal("5")
        producto.activo = True

        cliente = db.session.query(Cliente).filter_by(razon_social=CLIENTE_PRUEBA).first()
        if cliente is None:
            cliente = Cliente(razon_social=CLIENTE_PRUEBA)
            db.session.add(cliente)
        cliente.activo = True

        db.session.commit()
        return producto.id, cliente.id


def stock_actual(app, id_producto) -> Decimal:
    with app.app_context():
        return db.session.get(Producto, id_producto).stock


def main() -> None:
    app = crear_app()
    id_producto, id_cliente = preparar(app)

    c = app.test_client()
    c.post(
        "/login",
        data={
            "email": "santiago@grupo21.test",
            "contrasena": "grupo21.santiago",
            "csrf": csrf(c, "/login"),
        },
    )

    # -----------------------------------------------------------------------
    print("\n--- CRUD de clientes ---")

    respuesta = c.post(
        "/clientes/nuevo",
        data={
            "razon_social": "Ferretería Industrial del Norte",
            "documento": DOCUMENTO_DE_PRUEBA,
            "email": "ventas@ferreteria-norte.test",
            "csrf": csrf(c, "/clientes/nuevo"),
        },
    )
    assert respuesta.status_code == 302, respuesta.status_code
    ok(1, "Alta de cliente válida")

    html = c.post(
        "/clientes/nuevo",
        data={
            "razon_social": "Otro nombre",
            "documento": DOCUMENTO_DE_PRUEBA,
            "csrf": csrf(c, "/clientes/nuevo"),
        },
    ).get_data(as_text=True)
    assert "Ya hay un cliente con ese documento" in html
    ok(2, "Documento duplicado rechazado")

    html = c.post(
        "/clientes/nuevo",
        data={"razon_social": "Sin documento A", "csrf": csrf(c, "/clientes/nuevo")},
    ).get_data(as_text=True)
    respuesta = c.post(
        "/clientes/nuevo",
        data={"razon_social": "Sin documento B", "csrf": csrf(c, "/clientes/nuevo")},
    )
    assert respuesta.status_code == 302, "dos clientes sin documento deben convivir"
    ok(3, "Dos clientes sin documento conviven sin chocar")

    # -----------------------------------------------------------------------
    print("\n--- CU-01: abrir una venta ---")

    respuesta = c.post(
        "/ventas/nueva",
        data={
            "cliente_id": id_cliente,
            "observaciones": "Venta de prueba automatizada",
            "csrf": csrf(c, "/ventas/nueva"),
        },
    )
    assert respuesta.status_code == 302, respuesta.status_code
    id_venta = int(respuesta.headers["Location"].rstrip("/").split("/")[-1])
    ok(4, f"Venta #{id_venta} abierta en estado BORRADOR")

    html = c.post(
        "/ventas/nueva", data={"cliente_id": "", "csrf": csrf(c, "/ventas/nueva")}
    ).get_data(as_text=True)
    assert "Elegí un cliente" in html
    ok(5, "No deja abrir una venta sin cliente")

    # -----------------------------------------------------------------------
    print("\n--- CU-02: agregar productos ---")

    ruta_venta = f"/ventas/{id_venta}"

    c.post(
        f"{ruta_venta}/lineas",
        data={"producto_id": id_producto, "cantidad": "10", "csrf": csrf(c, ruta_venta)},
    )
    assert stock_actual(app, id_producto) == STOCK_INICIAL, "el borrador NO debe tocar el stock"
    ok(6, "Renglón agregado — el stock sigue intacto (el borrador no lo toca)")

    html = c.post(
        f"{ruta_venta}/lineas",
        data={"producto_id": id_producto, "cantidad": "5", "csrf": csrf(c, ruta_venta)},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "ya está en la venta" in aviso(html)
    ok(7, "Rechaza repetir el mismo producto en la venta")

    html = c.post(
        f"{ruta_venta}/lineas",
        data={"producto_id": id_producto, "cantidad": "0", "csrf": csrf(c, ruta_venta)},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "mayor a 0" in aviso(html)
    ok(8, "Rechaza cantidad cero")

    # -----------------------------------------------------------------------
    print("\n--- CU-04: confirmar la venta ---")

    html = c.post(
        f"{ruta_venta}/confirmar", data={"csrf": csrf(c, ruta_venta)}, follow_redirects=True
    ).get_data(as_text=True)
    assert "confirmada" in aviso(html, "exito")

    esperado = STOCK_INICIAL - 10
    assert stock_actual(app, id_producto) == esperado, stock_actual(app, id_producto)
    ok(9, f"Confirmada: el stock bajó de {STOCK_INICIAL} a {esperado}")

    with app.app_context():
        movimientos = (
            db.session.query(MovimientoStock)
            .filter_by(venta_id=id_venta)
            .order_by(MovimientoStock.id)
            .all()
        )
        assert len(movimientos) == 1 and movimientos[0].tipo == "EGRESO"
        assert movimientos[0].stock_resultante == esperado
        ok(10, f"Quedó el movimiento EGRESO con stock resultante {esperado}")

    html = c.post(
        f"{ruta_venta}/lineas",
        data={"producto_id": id_producto, "cantidad": "1", "csrf": csrf(c, ruta_venta)},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "no admite cambios" in aviso(html)
    ok(11, "Una venta confirmada ya no admite cambios")

    html = c.post(
        f"{ruta_venta}/confirmar", data={"csrf": csrf(c, ruta_venta)}, follow_redirects=True
    ).get_data(as_text=True)
    assert "ya estaba confirmada" in aviso(html)
    ok(12, "No se puede confirmar dos veces")

    # -----------------------------------------------------------------------
    print("\n--- Stock insuficiente ---")

    respuesta = c.post(
        "/ventas/nueva", data={"cliente_id": id_cliente, "csrf": csrf(c, "/ventas/nueva")}
    )
    id_venta2 = int(respuesta.headers["Location"].rstrip("/").split("/")[-1])
    ruta_venta2 = f"/ventas/{id_venta2}"

    html = c.post(
        f"{ruta_venta2}/lineas",
        data={"producto_id": id_producto, "cantidad": "9999", "csrf": csrf(c, ruta_venta2)},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "Stock insuficiente" in aviso(html)
    ok(13, "Rechaza vender más de lo disponible")

    html = c.post(
        f"{ruta_venta2}/confirmar",
        data={"csrf": csrf(c, ruta_venta2)},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "sin renglones" in aviso(html)
    ok(14, "No se puede confirmar una venta sin renglones")

    # -----------------------------------------------------------------------
    print("\n--- CU-05: anular la venta ---")

    html = c.post(
        f"{ruta_venta}/anular", data={"csrf": csrf(c, f"{ruta_venta}/anular")},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "anulada" in aviso(html, "exito")

    assert stock_actual(app, id_producto) == STOCK_INICIAL, stock_actual(app, id_producto)
    ok(15, f"Anulada: el stock volvió a {STOCK_INICIAL}")

    with app.app_context():
        movimientos = (
            db.session.query(MovimientoStock)
            .filter_by(venta_id=id_venta)
            .order_by(MovimientoStock.id)
            .all()
        )
        tipos = [m.tipo for m in movimientos]
        assert tipos == ["EGRESO", "INGRESO"], tipos
        ok(16, "El libro mayor quedó simétrico: EGRESO por la venta, INGRESO por la anulación")

        venta = db.session.get(Venta, id_venta)
        assert venta.estado == "ANULADA"
        assert venta.confirmada_en is not None and venta.anulada_en is not None
        ok(17, "La venta se conserva con sus dos fechas: no se borró")

    html = c.post(
        f"{ruta_venta}/anular", data={"csrf": csrf(c, f"{ruta_venta}/anular")},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "Solo se puede anular una venta confirmada" in aviso(html)
    ok(18, "No se puede anular dos veces")

    # -----------------------------------------------------------------------
    print("\n--- CU-08: alta de cliente desde la venta ---")

    html = c.get("/ventas/nueva").get_data(as_text=True)
    assert "/clientes/nuevo?volver=/ventas/nueva" in html
    ok(19, "La pantalla de venta ofrece cargar un cliente sin perder el paso")

    respuesta = c.post(
        "/clientes/nuevo",
        data={
            "razon_social": "Cliente creado desde la venta",
            "volver": "/ventas/nueva",
            "csrf": csrf(c, "/clientes/nuevo?volver=/ventas/nueva"),
        },
    )
    assert respuesta.headers["Location"].startswith("/ventas/nueva?cliente=")
    ok(20, "Al guardarlo, vuelve a la venta con el cliente ya seleccionado")

    respuesta = c.post(
        "/clientes/nuevo",
        data={
            "razon_social": "Control de destino externo",
            "volver": "https://sitio-externo.test",
            "csrf": csrf(c, "/clientes/nuevo"),
        },
    )
    assert respuesta.headers["Location"].endswith("/clientes/")
    ok(21, "Un destino de vuelta externo se ignora (no sirve para phishing)")

    # -----------------------------------------------------------------------
    print("\n--- Limpieza ---")
    with app.app_context():
        for razon in CLIENTES_DE_PRUEBA + (CLIENTE_PRUEBA,):
            cliente = db.session.query(Cliente).filter_by(razon_social=razon).first()
            if cliente:
                cliente.activo = False

        producto = db.session.get(Producto, id_producto)
        producto.activo = False
        db.session.commit()
    print("  Los datos de prueba quedaron desactivados.")

    print("\nLas 21 comprobaciones pasaron.\n")


if __name__ == "__main__":
    main()
