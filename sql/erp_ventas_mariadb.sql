-- =============================================================================
-- ERP grupo21 — SIMAS 2026
-- Modelado del flujo de VENTA DE PRODUCTOS en MariaDB.
--
-- Objetivo: registrar ventas a clientes descontando stock de forma que la
-- integridad de los datos quede garantizada POR LA BASE, no por la aplicación.
--
-- Uso:  mysql -u root -p < erp_ventas_mariadb.sql
-- =============================================================================

DROP DATABASE IF EXISTS erp_grupo21;
CREATE DATABASE erp_grupo21
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE erp_grupo21;

-- Modo estricto: que un dato inválido falle, en vez de guardarse truncado.
SET SESSION sql_mode = 'STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION';

-- =============================================================================
-- 1. TABLAS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Cliente
-- -----------------------------------------------------------------------------
CREATE TABLE cliente (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  razon_social  VARCHAR(150)  NOT NULL,
  documento     VARCHAR(20)   UNIQUE,           -- CUIT / DNI
  email         VARCHAR(150),
  telefono      VARCHAR(30),
  direccion     VARCHAR(200),
  -- Baja lógica: nunca se borra un cliente con ventas históricas.
  activo        BOOLEAN       NOT NULL DEFAULT TRUE,
  creado_en     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_cliente_razon (razon_social),
  INDEX idx_cliente_activo (activo)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Producto
-- Identificado por un código único, con precio y stock.
-- -----------------------------------------------------------------------------
CREATE TABLE producto (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo        VARCHAR(30)   NOT NULL UNIQUE,
  nombre        VARCHAR(150)  NOT NULL,
  descripcion   TEXT,
  -- DECIMAL y no FLOAT: con plata, los errores de redondeo no se perdonan.
  precio        DECIMAL(12,2) NOT NULL,
  stock         DECIMAL(12,2) NOT NULL DEFAULT 0,
  stock_minimo  DECIMAL(12,2) NOT NULL DEFAULT 0,
  activo        BOOLEAN       NOT NULL DEFAULT TRUE,
  creado_en     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  -- Última línea de defensa: aunque falle toda la lógica de arriba,
  -- la base se niega a dejar el stock en negativo o el precio en cero.
  CONSTRAINT chk_producto_precio       CHECK (precio > 0),
  CONSTRAINT chk_producto_stock        CHECK (stock >= 0),
  CONSTRAINT chk_producto_stock_minimo CHECK (stock_minimo >= 0),

  INDEX idx_producto_nombre (nombre),
  INDEX idx_producto_activo (activo)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Venta (cabecera)
-- Ciclo de vida: BORRADOR -> CONFIRMADA -> (ANULADA)
--   BORRADOR   se arma libremente y NO toca el stock.
--   CONFIRMADA descuenta stock y queda inmutable.
--   ANULADA    devuelve el stock; no borra nada.
-- -----------------------------------------------------------------------------
CREATE TABLE venta (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cliente_id    INT UNSIGNED  NOT NULL,
  fecha         TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado        ENUM('BORRADOR','CONFIRMADA','ANULADA') NOT NULL DEFAULT 'BORRADOR',
  total         DECIMAL(12,2) NOT NULL DEFAULT 0,
  observaciones VARCHAR(255),
  confirmada_en DATETIME,
  anulada_en    DATETIME,

  CONSTRAINT fk_venta_cliente
    FOREIGN KEY (cliente_id) REFERENCES cliente(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  CONSTRAINT chk_venta_total CHECK (total >= 0),

  INDEX idx_venta_cliente (cliente_id),
  INDEX idx_venta_estado_fecha (estado, fecha)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Detalle de venta (renglones)
-- -----------------------------------------------------------------------------
CREATE TABLE detalle_venta (
  id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  venta_id        INT UNSIGNED  NOT NULL,
  producto_id     INT UNSIGNED  NOT NULL,
  cantidad        DECIMAL(12,2) NOT NULL,
  -- COPIA del precio al momento de la venta, no una referencia:
  -- si mañana cambia el precio del producto, esta venta no se altera.
  precio_unitario DECIMAL(12,2) NOT NULL,
  subtotal        DECIMAL(12,2) NOT NULL,

  CONSTRAINT fk_detalle_venta
    FOREIGN KEY (venta_id) REFERENCES venta(id)
    ON DELETE CASCADE ON UPDATE CASCADE,   -- un renglón sin su venta no significa nada
  CONSTRAINT fk_detalle_producto
    FOREIGN KEY (producto_id) REFERENCES producto(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,  -- no se borra un producto ya vendido

  CONSTRAINT chk_detalle_cantidad CHECK (cantidad > 0),
  CONSTRAINT chk_detalle_precio   CHECK (precio_unitario >= 0),

  -- Un mismo producto no se repite dos veces en la misma venta.
  UNIQUE KEY uq_detalle_venta_producto (venta_id, producto_id),
  INDEX idx_detalle_producto (producto_id)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Movimiento de stock — el "libro mayor" de las existencias.
-- producto.stock responde "¿cuánto hay?"; esta tabla responde "¿cómo se llegó
-- a ese número?". Es lo que hace auditable al sistema.
-- -----------------------------------------------------------------------------
CREATE TABLE movimiento_stock (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  producto_id      INT UNSIGNED  NOT NULL,
  tipo             ENUM('INGRESO','EGRESO','AJUSTE') NOT NULL,
  origen           ENUM('VENTA','ANULACION','COMPRA','AJUSTE_MANUAL') NOT NULL,
  cantidad         DECIMAL(12,2) NOT NULL,   -- siempre positiva; el signo lo da `tipo`
  stock_resultante DECIMAL(12,2) NOT NULL,   -- foto del stock después del movimiento
  venta_id         INT UNSIGNED,
  motivo           VARCHAR(255),
  fecha            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_movimiento_producto
    FOREIGN KEY (producto_id) REFERENCES producto(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_movimiento_venta
    FOREIGN KEY (venta_id) REFERENCES venta(id)
    ON DELETE SET NULL ON UPDATE CASCADE,

  CONSTRAINT chk_movimiento_cantidad CHECK (cantidad > 0),

  INDEX idx_movimiento_producto_fecha (producto_id, fecha),
  INDEX idx_movimiento_venta (venta_id)
) ENGINE=InnoDB;

-- =============================================================================
-- 2. TRIGGERS — la integridad del stock vive acá
-- =============================================================================

DELIMITER $$

-- -----------------------------------------------------------------------------
-- Al agregar un renglón: completar precio y subtotal desde el producto.
-- Valida que el producto esté activo y que haya stock suficiente.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_detalle_before_insert
BEFORE INSERT ON detalle_venta
FOR EACH ROW
BEGIN
  DECLARE v_precio  DECIMAL(12,2);
  DECLARE v_stock   DECIMAL(12,2);
  DECLARE v_activo  BOOLEAN;
  DECLARE v_estado  VARCHAR(20);

  -- La venta tiene que existir y estar abierta.
  SELECT estado INTO v_estado FROM venta WHERE id = NEW.venta_id;
  IF v_estado <> 'BORRADOR' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'No se pueden agregar renglones: la venta no está en BORRADOR';
  END IF;

  -- FOR UPDATE bloquea la fila del producto hasta el fin de la transacción:
  -- sin esto, dos ventas simultáneas podrían leer el mismo stock y vender de más.
  SELECT precio, stock, activo
    INTO v_precio, v_stock, v_activo
    FROM producto
   WHERE id = NEW.producto_id
     FOR UPDATE;

  IF NOT v_activo THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El producto está dado de baja y no puede venderse';
  END IF;

  IF v_stock < NEW.cantidad THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Stock insuficiente para la cantidad solicitada';
  END IF;

  -- Si no se especifica precio, se toma el vigente del producto.
  IF NEW.precio_unitario IS NULL OR NEW.precio_unitario = 0 THEN
    SET NEW.precio_unitario = v_precio;
  END IF;

  SET NEW.subtotal = NEW.cantidad * NEW.precio_unitario;
END$$

-- -----------------------------------------------------------------------------
-- Después de agregar un renglón: recalcular el total de la venta.
-- El stock NO se toca todavía: se descuenta recién al confirmar.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_detalle_after_insert
AFTER INSERT ON detalle_venta
FOR EACH ROW
BEGIN
  UPDATE venta
     SET total = (SELECT COALESCE(SUM(subtotal), 0)
                    FROM detalle_venta
                   WHERE venta_id = NEW.venta_id)
   WHERE id = NEW.venta_id;
END$$

-- -----------------------------------------------------------------------------
-- Al borrar un renglón (solo posible en BORRADOR): recalcular el total.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_detalle_after_delete
AFTER DELETE ON detalle_venta
FOR EACH ROW
BEGIN
  UPDATE venta
     SET total = (SELECT COALESCE(SUM(subtotal), 0)
                    FROM detalle_venta
                   WHERE venta_id = OLD.venta_id)
   WHERE id = OLD.venta_id;
END$$

-- -----------------------------------------------------------------------------
-- Cambios de estado de la venta: es acá donde el stock se mueve.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_venta_after_update
AFTER UPDATE ON venta
FOR EACH ROW
BEGIN
  DECLARE v_fin      INT DEFAULT 0;
  DECLARE v_prod     INT UNSIGNED;
  DECLARE v_cant     DECIMAL(12,2);
  DECLARE v_stock    DECIMAL(12,2);

  DECLARE cur CURSOR FOR
    SELECT producto_id, cantidad FROM detalle_venta WHERE venta_id = NEW.id;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = 1;

  -- ---------- BORRADOR -> CONFIRMADA: descontar stock ----------
  IF OLD.estado = 'BORRADOR' AND NEW.estado = 'CONFIRMADA' THEN
    OPEN cur;
    leer: LOOP
      FETCH cur INTO v_prod, v_cant;
      IF v_fin = 1 THEN LEAVE leer; END IF;

      -- Descuento atómico: el CHECK (stock >= 0) aborta si no alcanza.
      UPDATE producto SET stock = stock - v_cant WHERE id = v_prod;

      SELECT stock INTO v_stock FROM producto WHERE id = v_prod;

      INSERT INTO movimiento_stock
             (producto_id, tipo, origen, cantidad, stock_resultante, venta_id, motivo)
      VALUES (v_prod, 'EGRESO', 'VENTA', v_cant, v_stock, NEW.id,
              CONCAT('Venta #', NEW.id));
    END LOOP;
    CLOSE cur;

  -- ---------- CONFIRMADA -> ANULADA: devolver stock ----------
  ELSEIF OLD.estado = 'CONFIRMADA' AND NEW.estado = 'ANULADA' THEN
    OPEN cur;
    leer2: LOOP
      FETCH cur INTO v_prod, v_cant;
      IF v_fin = 1 THEN LEAVE leer2; END IF;

      UPDATE producto SET stock = stock + v_cant WHERE id = v_prod;

      SELECT stock INTO v_stock FROM producto WHERE id = v_prod;

      INSERT INTO movimiento_stock
             (producto_id, tipo, origen, cantidad, stock_resultante, venta_id, motivo)
      VALUES (v_prod, 'INGRESO', 'ANULACION', v_cant, v_stock, NEW.id,
              CONCAT('Anulación de venta #', NEW.id));
    END LOOP;
    CLOSE cur;
  END IF;
END$$

-- -----------------------------------------------------------------------------
-- Una venta confirmada es inmutable: solo se le permite pasar a ANULADA.
-- Sin esto, cualquiera podría reescribir el historial y los números dejarían
-- de cerrar.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_venta_before_update
BEFORE UPDATE ON venta
FOR EACH ROW
BEGIN
  IF OLD.estado = 'CONFIRMADA'
     AND NEW.estado <> 'ANULADA'
     AND NEW.estado <> OLD.estado THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Una venta confirmada solo puede anularse';
  END IF;

  IF OLD.estado = 'ANULADA' AND NEW.estado <> 'ANULADA' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Una venta anulada no puede reabrirse';
  END IF;

  IF NEW.estado = 'CONFIRMADA' AND OLD.estado = 'BORRADOR' THEN
    IF (SELECT COUNT(*) FROM detalle_venta WHERE venta_id = NEW.id) = 0 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se puede confirmar una venta sin renglones';
    END IF;
    SET NEW.confirmada_en = NOW();
  END IF;

  IF NEW.estado = 'ANULADA' AND OLD.estado <> 'ANULADA' THEN
    SET NEW.anulada_en = NOW();
  END IF;
END$$

-- -----------------------------------------------------------------------------
-- Los renglones de una venta confirmada no se tocan.
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_detalle_before_delete
BEFORE DELETE ON detalle_venta
FOR EACH ROW
BEGIN
  DECLARE v_estado VARCHAR(20);
  SELECT estado INTO v_estado FROM venta WHERE id = OLD.venta_id;
  IF v_estado = 'CONFIRMADA' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'No se pueden borrar renglones de una venta confirmada';
  END IF;
END$$

DELIMITER ;

-- =============================================================================
-- 3. PROCEDIMIENTO: registrar una venta completa
-- =============================================================================

DELIMITER $$

-- Confirma la venta dentro de una transacción: si algo falla (stock, estado),
-- se deshace TODO. Nunca queda media venta registrada.
CREATE PROCEDURE sp_confirmar_venta(IN p_venta_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;
    UPDATE venta SET estado = 'CONFIRMADA' WHERE id = p_venta_id;
  COMMIT;
END$$

DELIMITER ;

-- =============================================================================
-- 4. VISTAS
-- =============================================================================

-- Productos que necesitan reposición: insumo de la sugerencia de compra.
CREATE VIEW v_productos_a_reponer AS
SELECT p.id,
       p.codigo,
       p.nombre,
       p.stock,
       p.stock_minimo,
       (p.stock_minimo - p.stock) AS faltante
  FROM producto p
 WHERE p.activo = TRUE
   AND p.stock <= p.stock_minimo;

-- Ventas con su cliente y cantidad de renglones.
CREATE VIEW v_ventas_resumen AS
SELECT v.id,
       v.fecha,
       v.estado,
       c.razon_social       AS cliente,
       COUNT(d.id)          AS renglones,
       v.total
  FROM venta v
  JOIN cliente c       ON c.id = v.cliente_id
  LEFT JOIN detalle_venta d ON d.venta_id = v.id
 GROUP BY v.id, v.fecha, v.estado, c.razon_social, v.total;

-- =============================================================================
-- 5. DATOS DE PRUEBA
-- =============================================================================

INSERT INTO cliente (razon_social, documento, email, telefono) VALUES
  ('Metalúrgica del Litoral S.A.', '30-71234567-8', 'compras@metlitoral.com.ar', '342-4567890'),
  ('Distribuidora Santa Fe SRL',   '30-70987654-3', 'ventas@distsf.com.ar',      '342-4112233'),
  ('Juan Pérez',                   '20-34567890-1', 'jperez@mail.com',           '342-5556677');

INSERT INTO producto (codigo, nombre, descripcion, precio, stock, stock_minimo) VALUES
  ('PRD-001', 'Chapa galvanizada 1x2m', 'Espesor 0.9mm',        18500.00, 120, 20),
  ('PRD-002', 'Perfil C 100x50',        'Barra de 6 metros',     9750.50, 300, 50),
  ('PRD-003', 'Tornillo autoperforante','Caja x 500 unidades',   4200.00,  45, 10),
  ('PRD-004', 'Electrodo 2.5mm',        'Caja x 5kg',           15300.00,   8, 15),
  ('PRD-005', 'Pintura antióxido 4L',   'Color gris',           22900.00,  60, 12);

-- ---- Venta de ejemplo: se arma, se confirma y descuenta stock ----
INSERT INTO venta (cliente_id, observaciones) VALUES (1, 'Pedido telefónico');
SET @venta = LAST_INSERT_ID();

-- precio_unitario en 0 => el trigger toma el precio vigente del producto.
INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario, subtotal)
VALUES (@venta, 1, 10, 0, 0),
       (@venta, 2, 25, 0, 0);

CALL sp_confirmar_venta(@venta);

-- =============================================================================
-- 6. CONSULTAS DE VERIFICACIÓN
-- =============================================================================

-- El stock de PRD-001 debe haber bajado de 120 a 110, y el de PRD-002 de 300 a 275.
SELECT codigo, nombre, stock FROM producto ORDER BY codigo;

-- La venta quedó confirmada y con su total calculado solo.
SELECT * FROM v_ventas_resumen;

-- Trazabilidad: cada unidad que salió tiene su asiento.
SELECT m.fecha, p.codigo, m.tipo, m.origen, m.cantidad, m.stock_resultante, m.motivo
  FROM movimiento_stock m
  JOIN producto p ON p.id = m.producto_id
 ORDER BY m.fecha, m.id;

-- Productos bajo el mínimo (PRD-004 debería aparecer).
SELECT * FROM v_productos_a_reponer;

-- =============================================================================
-- 7. PRUEBAS DE INTEGRIDAD (descomentar para verificar que la base se defiende)
-- =============================================================================

-- (a) Vender más de lo que hay -> debe fallar con 'Stock insuficiente'
-- INSERT INTO venta (cliente_id) VALUES (2);
-- INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario, subtotal)
--   VALUES (LAST_INSERT_ID(), 4, 999, 0, 0);

-- (b) Modificar una venta confirmada -> debe fallar
-- UPDATE venta SET estado = 'BORRADOR' WHERE id = 1;

-- (c) Borrar un producto ya vendido -> debe fallar por la foreign key
-- DELETE FROM producto WHERE id = 1;

-- (d) Anular la venta -> el stock vuelve a 120 y 300
-- UPDATE venta SET estado = 'ANULADA' WHERE id = 1;
-- SELECT codigo, stock FROM producto ORDER BY codigo;
