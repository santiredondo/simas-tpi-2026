# Usuarios y autenticación — Campos, diseño y seguridad

Workshop 4 · Checkpoint 1 · Team **grupo21**

---

## 1. Campos de la tabla `usuario`

| Campo | Tipo | Obligatorio | Único | Observación |
| --- | --- | --- | --- | --- |
| `id` | Entero | Sí | Sí | Clave primaria, se genera automáticamente |
| `nombre` | Texto (100) | Sí | No | Nombre y apellido de la persona |
| `email` | Texto (150) | Sí | **Sí** | Es el usuario de ingreso al sistema |
| `contrasena_hash` | Texto (255) | Sí | No | **Se guarda hasheada, nunca en texto plano** |
| `rol_id` | Entero | Sí | No | Relación con la tabla `rol` |
| `activo` | Booleano | Sí | No | Baja lógica, por defecto `true` |
| `fecha_alta` | Fecha y hora | Sí | No | Por defecto, el momento del alta |
| `ultimo_acceso` | Fecha y hora | No | No | Se actualiza en cada ingreso exitoso |

### Por qué 255 caracteres para el hash

El hash no es solo el "resultado cifrado": el campo guarda **método, parámetros, salt y digest** juntos. Un hash de scrypt real se ve así:

```
scrypt:32768:8:1$Hv5qqrgxQbfp7ezp$9b7a5c8eae4...
└─método─┘└params┘ └────salt────┘ └──digest──┘
```

Dimensionar el campo con el largo de una contraseña es un error clásico: el hash se trunca y nadie puede volver a entrar.

### Por qué `ultimo_acceso`

No estaba en la especificación original, pero cuesta un campo y responde dos preguntas que siempre aparecen: *¿esta cuenta se sigue usando?* y *¿alguien entró cuando no debía?*

---

## 2. Campos de la tabla `rol`

Los permisos se asignan **al rol y no a cada persona**. Así, cambiar lo que puede hacer un puesto no obliga a modificar usuario por usuario.

| Campo | Tipo | Observación |
| --- | --- | --- |
| `id` | Entero | Clave primaria |
| `nombre` | Texto (50) | ADMINISTRADOR, VENDEDOR, COMPRADOR |
| `descripcion` | Texto (200) | Opcional |

| Rol | Qué puede hacer |
| --- | --- |
| **ADMINISTRADOR** | Todo, incluida la administración de usuarios |
| **VENDEDOR** | Registrar ventas y gestionar clientes |
| **COMPRADOR** | Gestionar productos y reponer stock |

---

## 3. Cómo se guarda la contraseña

La contraseña **nunca se almacena**. Se almacena su *hash*: el resultado de una función de una sola dirección.

```
    Alta / cambio de contraseña          Ingreso al sistema
    ───────────────────────────          ──────────────────
    "clave12345"                         "clave12345" (tecleada)
         ↓ scrypt + salt aleatorio            ↓ scrypt + el MISMO salt
    scrypt:32768:8:1$Hv5q...$9b7a...     scrypt:32768:8:1$Hv5q...$9b7a...
         ↓                                    ↓
    se guarda en la base          ←→    ¿coinciden? → acceso permitido
```

Se puede **verificar** si una contraseña coincide, pero no se puede **recuperar** la original a partir del hash.

### Las tres decisiones de seguridad

**1. scrypt, no MD5 ni SHA-256.**
MD5 y SHA están diseñados para ser *rápidos*, y eso juega en contra: una placa de video prueba miles de millones por segundo. scrypt es deliberadamente lento y consume mucha memoria, lo que encarece el ataque por fuerza bruta.

**2. Cada hash lleva su propio salt** (un valor aleatorio).
Sin salt, dos personas con la misma contraseña tendrían el mismo hash, y se podrían usar tablas precalculadas (*rainbow tables*) para revertirlo. Con salt, el mismo texto da hashes distintos:

```
admin1234    → scrypt:32768:8:1$Hv5qqrgxQbfp7ezp$9b7a5c8eae4...
admin1234    → scrypt:32768:8:1$EBWo2RPmHGQnCvSv$4ca9364574e...
                                └ salt distinto ┘
```

**3. Ni los administradores pueden ver las contraseñas.**
El formulario de edición no las precarga, porque no existen para precargar. Si alguien la olvida, se le asigna una nueva; no se le "consulta" la vieja.

---

## 4. Autenticación: cómo funciona el acceso

### Ingreso

1. La persona escribe email y contraseña.
2. Se busca el usuario por email y se verifica que esté **activo**.
3. Se compara la contraseña contra el hash guardado.
4. Si coincide, se guarda el `id` del usuario en la **cookie de sesión**, que Flask firma criptográficamente: el navegador no puede modificarla para hacerse pasar por otro.
5. Se registra `ultimo_acceso`.

### Mensaje de error genérico, a propósito

Ante un email inexistente o una contraseña equivocada, el sistema responde lo mismo: **"Email o contraseña incorrectos"**.

Distinguirlos le confirmaría a un atacante qué cuentas existen, que es el primer paso para atacarlas.

### El permiso se verifica en cada pedido

Antes de cada request se recarga el usuario desde la base. Si fue dado de baja mientras tenía la sesión abierta, **se lo desloguea en el acto**. Verificar solo al momento del login dejaría la puerta abierta hasta que cerrara el navegador.

### Puerta de entrada única

Todas las rutas exigen sesión, salvo el propio login y los archivos estáticos. La lista de excepciones es explícita y corta.

Proteger vista por vista es frágil: alcanza con olvidarse un decorador en una ruta nueva para dejar una puerta abierta.

### Protección contra redirección maliciosa

Al entrar sin sesión, el sistema recuerda a dónde ibas (`/login?siguiente=/usuarios/`) para llevarte ahí después. Solo se aceptan rutas internas: un `siguiente` con una URL externa convertiría el login en un trampolín de phishing.

---

## 5. Reglas de negocio del CRUD

| Regla | Por qué |
| --- | --- |
| Solo el rol ADMINISTRADOR entra a `/usuarios` | Quien administra usuarios administra los permisos de todo el sistema |
| No podés cambiar **tu propio rol** | Si fuera el único administrador, el sistema quedaría sin nadie que pueda administrarlo |
| No podés **darte de baja a vos mismo** | Sería quedarse afuera en el acto |
| La contraseña es opcional al editar | Se deja vacía para conservar la actual; no se puede precargar porque no existe en claro |
| La baja es lógica | Las operaciones registran quién las hizo: borrar el usuario dejaría ese historial sin autor |
| El control de permisos vive en el servidor | Esconder un botón no es seguridad: la URL se puede escribir a mano |

---

## 6. Diseño de pantallas

### 6.1 Login

```
              ┌──────────────────────────────┐
              │  ERP grupo21                 │
              │  Ingresá con tu cuenta.      │
              │                              │
              │  Email                       │
              │  ┌────────────────────────┐  │
              │  │                        │  │
              │  └────────────────────────┘  │
              │                              │
              │  Contraseña                  │
              │  ┌────────────────────────┐  │
              │  │ ••••••••               │  │
              │  └────────────────────────┘  │
              │                              │
              │  [       Ingresar        ]   │
              └──────────────────────────────┘
```

Con credenciales incorrectas, el mismo formulario con el aviso arriba y el email conservado (la contraseña no).

### 6.2 Listado de usuarios

```
┌────────────────────────────────────────────────────────────────────────┐
│ ERP grupo21   Productos │ Clientes │ Ventas │ Usuarios   Admin · Salir │
├────────────────────────────────────────────────────────────────────────┤
│  Usuarios                                      [ + Nuevo usuario ]     │
│  3 usuarios activos                                                    │
│  ┌──────────────────────┐ ┌──────────────┐ ┌────────┐                  │
│  │ Buscar...            │ │ Solo activos▾│ │ Buscar │                  │
│  └──────────────────────┘ └──────────────┘ └────────┘                  │
│  ┌──────────────┬─────────────────────┬───────────────┬──────────────┐ │
│  │ NOMBRE       │ EMAIL               │ ROL           │ ÚLT. ACCESO  │ │
│  ├──────────────┼─────────────────────┼───────────────┼──────────────┤ │
│  │ Admin (vos)  │ admin@grupo21.test  │(Administrador)│ 09/10 14:22  │ │
│  │ Lautaro R.   │ lautaro@...         │ (Vendedor)    │ Nunca ingresó│ │
│  └──────────────┴─────────────────────┴───────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

El link "Usuarios" en la barra **solo aparece para administradores** — y además la ruta está protegida en el servidor, que es lo que realmente cuenta.

### 6.3 Alta / edición

Formulario con nombre, email, rol, y un bloque aparte para la contraseña (con repetición). Al editar, ese bloque aclara: *"Dejá estos campos vacíos para conservar la contraseña actual"*.

---

## 7. Verificación

29 pruebas contra MariaDB, incluidas las que **deben fallar**:

| # | Prueba | Resultado |
| --- | --- | --- |
| 1-2 | Sin sesión, `/productos` y `/usuarios` redirigen al login | ✅ |
| 3-4 | Contraseña incorrecta y email inexistente | HTTP 401, mismo mensaje ✅ |
| 5-6 | Login de administrador y acceso a `/usuarios` | ✅ |
| 7-9 | Vendedor entra, pero `/usuarios` lo rebota | ✅ |
| 10-14 | Alta válida; email duplicado, contraseña corta, contraseñas distintas y email inválido rechazados | ✅ |
| 15-16 | Editar sin tocar la contraseña la conserva | ✅ |
| 17-18 | No puede cambiarse el rol ni darse de baja a sí mismo | ✅ |
| 19-21 | Cambio de contraseña: la vieja deja de servir, la nueva funciona | ✅ |
| 22-23 | Usuario dado de baja no puede ingresar | ✅ |
| 24 | Reactivación | ✅ |
| 25-27 | **Dar de baja a alguien con la sesión abierta lo expulsa en el próximo pedido** | ✅ |
| 28-29 | Logout invalida la sesión | ✅ |

### Comprobación de que el hash es real

```sql
SELECT email, LEFT(contrasena_hash, 45) AS hash, LENGTH(contrasena_hash) AS largo
  FROM usuario;
```

```
admin@grupo21.test      scrypt:32768:8:1$Hv5qqrgxQbfp7ezp$9b7a5c8eae4   162
vendedor@grupo21.test   scrypt:32768:8:1$EBWo2RPmHGQnCvSv$4ca9364574e   162
```

Ninguna contraseña aparece en texto plano, y los salts son distintos.

---

## 8. Los cinco pilares del flujo de autenticación

| Pilar | Qué significa | Cómo está resuelto |
| --- | --- | --- |
| **Autenticación** | Verificar que el usuario es quien dice ser | Login con email + contraseña, verificada contra el hash. Mensaje de error genérico para no revelar qué cuentas existen |
| **Autorización** | Determinar qué puede hacer según su rol | Tabla `rol` + decorador `rol_requerido`. `/usuarios` es exclusivo de ADMINISTRADOR, validado **en el servidor** |
| **Sesión** | Mantener el estado del usuario autenticado | Cookie firmada por Flask con el `id` del usuario. El permiso se revalida en cada pedido contra la base |
| **Cifrado y hashing** | No guardar contraseñas en texto plano | scrypt con salt aleatorio por usuario. La cookie viaja como `HttpOnly` y `SameSite=Lax` |
| **Caducidad y cierre de sesión** | Evitar que alguien use un login abandonado | La sesión vence a los **30 minutos de inactividad** (configurable). El plazo se renueva con cada pedido. Botón "Salir" que la invalida |

### El ejemplo de la consigna, resuelto

> *"Si un operador intenta ingresar al panel de administración → el sistema debe bloquearlo."*

Es exactamente la prueba 8 de la verificación. Un usuario con rol VENDEDOR que escribe `/usuarios/` a mano en la barra del navegador recibe un `302` hacia el listado de productos y el mensaje *"No tenés permisos para esa sección"*.

**El link no aparece en su barra de navegación, pero eso es cosmética.** Lo que lo bloquea de verdad es la validación del servidor: esconder un botón no es seguridad, porque la URL se puede escribir a mano, guardar en favoritos o recibir por mensaje.

### Por qué la caducidad cuenta la inactividad y no el tiempo total

Si venciera a las 8 horas de conectado, a alguien se le cortaría la sesión en mitad de una carga. Si vence a los 30 minutos **sin actividad**, el que está trabajando no se entera, y la máquina del depósito que quedó abierta deja de ser un problema.

```
   login ──[trabaja]──[trabaja]──[trabaja]──────────────── 30 min sin tocar nada ──> caduca
            ↑ cada pedido renueva el plazo
```

Verificado con `prueba_caducidad.py`, que levanta la aplicación con una sesión de 2 segundos: sin actividad caduca, con actividad constante se mantiene viva.

### Protecciones de la cookie

| Atributo | Para qué |
| --- | --- |
| **Firmada** | El navegador no puede editarla para hacerse pasar por otro usuario |
| **HttpOnly** | JavaScript no puede leerla: aunque se cuele un script, no roba la sesión |
| **SameSite=Lax** | No se envía en pedidos que vienen de otro sitio: frena los CSRF más simples |
| **Secure** | Solo viaja por HTTPS (se activa al publicar; en local se usa http) |
