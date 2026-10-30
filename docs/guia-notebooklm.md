# Guía para armar el Checkpoint 2 en NotebookLM

Workshop 5 · Checkpoint 2 · Team **grupo21**

Lo que pide el checkpoint y con qué se resuelve:

| Pedido | Herramienta |
| --- | --- |
| Resumen de todo lo hecho en el ERP | Documento fuente + resumen generado por NotebookLM |
| Diagrama que resuma el funcionamiento | `docs/imagenes/diagrama_funcionamiento.png` + mapa mental de NotebookLM |
| Contenido multimedia promocional | Resumen en video o audio de NotebookLM |

---

## Paso 1 — Crear el notebook y cargar las fuentes

NotebookLM solo habla de lo que le das: no inventa ni busca en internet. Mientras mejores sean las fuentes, mejor sale todo lo demás.

1. Entrar a **notebooklm.google.com** e iniciar sesión.
2. **Crear un notebook nuevo** y llamarlo `ERP grupo21 — SIMA 2026`.
3. Subir estos archivos del repositorio como fuentes:

| Archivo | Para qué sirve |
| --- | --- |
| `docs/resumen-erp.md` | **La fuente principal.** Tiene el sistema completo explicado |
| `docs/modelado-de-procesos.md` | Módulos, entidades y flujos |
| `docs/clientes-y-ventas-diseno.md` | Casos de uso del flujo de ventas |
| `docs/usuarios-y-autenticacion.md` | Seguridad y autenticación |
| `docs/crud-productos-diseno.md` | Campos y pantallas de productos |
| `docs/decisiones-tecnicas.md` | El porqué de cada decisión |
| `README.md` | Estado del proyecto y cómo se ejecuta |

> **Si NotebookLM no acepta `.md`**, abrir el archivo en el navegador desde GitHub, copiar el texto y pegarlo como fuente de tipo "Texto copiado". El contenido es lo que importa, no el formato.

**Consejo:** empezá subiendo solo `resumen-erp.md` y generá el audio con eso. Es la fuente más limpia y da el mejor resultado. Las demás suman detalle, pero también ruido.

---

## Paso 2 — El resumen

Una vez cargadas las fuentes, NotebookLM genera solo un resumen del notebook. Para el entregable conviene pedir uno más específico.

**Prompt para pegar en el chat:**

```
Escribí un resumen ejecutivo del ERP, de entre 400 y 600 palabras,
para presentar ante la cátedra de Sistemas de Información para
Manufactura.

Estructuralo así:
1. Qué es el sistema y para qué sirve
2. Los módulos que tiene y qué hace cada uno
3. Cómo funciona el flujo de ventas y su impacto en el stock
4. Las decisiones de diseño que lo distinguen
5. Cómo se verificó que funciona

Escribí en español rioplatense, en tono profesional pero claro.
No uses viñetas en exceso: preferí párrafos que expliquen el porqué
de cada decisión, no solo qué hace el sistema.
```

Después, en el panel de la derecha, usar **"Documento informativo"** (Briefing doc) para tener una segunda versión más estructurada. Entre las dos sale el texto final.

---

## Paso 3 — El diagrama

Tenés dos opciones, y lo mejor es presentar **las dos**.

### 3.1 El diagrama que ya está hecho

`docs/imagenes/diagrama_funcionamiento.png` — muestra el sistema completo en cinco bandas: quién lo usa, la puerta de entrada de seguridad, los módulos, el flujo de ventas, dónde se guardan los datos y las reglas que lo gobiernan.

Es el que conviene poner en la presentación: está pensado para explicarse solo.

### 3.2 El mapa mental de NotebookLM

En el panel derecho, **Mapa mental** (Mind map). Lo genera a partir de las fuentes y queda interactivo: se puede expandir cada rama durante la defensa.

Si querés guiarlo antes de generarlo:

```
Armá un mapa conceptual del ERP organizado en cinco ramas principales:
1. Módulos funcionales (productos, clientes, ventas, usuarios)
2. Flujo de una venta (borrador, confirmada, anulada)
3. Modelo de datos (las nueve tablas y cómo se relacionan)
4. Seguridad (autenticación, autorización, sesión, hashing, caducidad)
5. Decisiones de diseño y su justificación

Para cada rama incluí los conceptos clave como sub-nodos.
```

---

## Paso 4 — El contenido multimedia promocional

Acá está lo más vistoso del checkpoint. NotebookLM ofrece dos formatos.

### 4.1 Resumen en video (recomendado para promocionar)

En el panel derecho: **Resumen en video** (Video Overview). Genera un video narrado con diapositivas a partir de las fuentes.

**Antes de generarlo**, usar la opción de personalizar y pegar esto:

```
Audiencia: una empresa de manufactura mediana que todavía lleva
el stock en planillas de cálculo.

Objetivo: mostrar por qué este ERP les resuelve un problema real.

Tono: profesional y directo, como una demostración de producto.
Nada de lenguaje publicitario exagerado.

Estructura sugerida:
- El problema: no saber cuánto stock hay realmente, y no poder
  explicar por qué el número es ese
- La solución: cada movimiento de stock queda registrado con su
  resultado, así el sistema puede rendir cuentas
- Los módulos, mostrados desde lo que resuelven y no desde su
  nombre técnico
- El flujo de una venta de punta a punta
- La seguridad: roles, contraseñas hasheadas y auditoría de accesos
- Cierre: es un sistema probado, con 87 pruebas verificadas

Duración objetivo: entre 3 y 5 minutos.
Idioma: español rioplatense.
```

### 4.2 Resumen en audio (el "podcast")

**Resumen de audio** (Audio Overview): dos locutores conversando sobre el material. Es el formato más llamativo de NotebookLM.

Personalizar con:

```
Conversación entre dos personas sobre el ERP desarrollado por el
grupo 21 para la materia Sistemas de Información para Manufactura.

Enfocate en estos tres puntos, que son los que lo hacen distinto:
1. Por qué el stock está "duplicado" a propósito: un campo para
   consultar rápido y una tabla de movimientos para auditar
2. Por qué nada se borra nunca, y por qué una venta confirmada
   se anula en lugar de editarse
3. Cómo se protegen las contraseñas y por qué el sistema responde
   lo mismo ante un email inexistente que ante una clave equivocada

Que uno de los dos haga las preguntas que haría alguien que no es
programador. Español rioplatense, tono distendido pero informado.
Duración: entre 5 y 8 minutos.
```

> **Importante:** el audio y el video pueden tardar varios minutos en generarse. No lo dejes para la hora antes de entregar.

### 4.3 Si piden algo editable

El video de NotebookLM se puede descargar. Si quieren además un guión escrito para grabar ustedes mismos, el apartado 5 de esta guía tiene uno listo.

---

## Paso 5 — Guión de respaldo (por si prefieren grabarlo ustedes)

Unos 90 segundos, pensado para acompañar capturas del sistema.

> **[Pantalla: listado de productos con la etiqueta "Reponer"]**
>
> La mayoría de las pymes de manufactura lleva el stock en una planilla.
> Funciona, hasta el día en que el número de la planilla no coincide con
> lo que hay en el depósito. Y nadie puede explicar por qué.
>
> **[Pantalla: pantalla de venta, agregando productos]**
>
> El ERP del grupo 21 resuelve eso. Se arma la venta, se eligen los
> productos, y el sistema avisa en el momento si no hay stock suficiente.
>
> **[Pantalla: confirmación de la venta]**
>
> Al confirmar, el stock se descuenta solo. Pero lo importante es lo que
> pasa detrás: cada unidad que sale queda registrada con la cantidad, el
> motivo y cuánto stock quedó en ese momento.
>
> **[Pantalla: tabla de movimientos de stock]**
>
> Así, cuando alguien pregunta por qué este producto tiene ciento diez
> unidades y no ciento veinte, el sistema lo responde. No hay que
> deducirlo.
>
> **[Pantalla: login y pantalla de usuarios]**
>
> Cada persona entra con su usuario y ve solo lo que le corresponde. Las
> contraseñas se guardan cifradas: ni los administradores pueden verlas.
> Y cada intento de acceso queda auditado.
>
> **[Pantalla: diagrama de funcionamiento]**
>
> Productos, clientes, ventas y usuarios. Ochenta y siete pruebas
> verificadas. Un sistema que no solo guarda datos: puede rendir cuentas
> de cada uno.
>
> **ERP grupo21. Sistemas de Información para Manufactura, 2026.**

---

## Paso 6 — Qué entregar

| Entregable | De dónde sale |
| --- | --- |
| Resumen escrito | Paso 2, combinando el chat y el documento informativo |
| Diagrama | `docs/imagenes/diagrama_funcionamiento.png` + captura del mapa mental |
| Multimedia | El video o audio generado en el paso 4, descargado |
| Link al notebook | NotebookLM permite compartirlo: conviene incluirlo |

---

## Advertencia sobre lo que genera la IA

**Leer todo antes de entregarlo.** NotebookLM se apoya en las fuentes, pero igual puede equivocarse: confundir un número, atribuir una característica al módulo equivocado, o afirmar algo con más seguridad de la que corresponde.

Tres datos para chequear específicamente, porque son los que más se citan y más fácil se distorsionan:

- **87 pruebas** en total (11 productos + 12 clientes + 12 ventas + 29 usuarios + 13 seguridad + 5 caducidad + 5 alta de cliente)
- **9 tablas** en la base de datos
- **3 roles**: Administrador, Vendedor, Comprador

Y lo más importante: **si el audio o el video afirma que algo funciona y no lo tenemos implementado**, hay que corregirlo. Por ejemplo, el módulo de compras y la sugerencia de reposición con IA todavía están pendientes. Entregar material que promete lo que el sistema no hace es el peor error posible en una defensa, porque la primera pregunta va a ser justamente sobre eso.
