const MODULOS = [
  {
    nombre: "Gestión de clientes",
    detalle: "Alta, consulta y actualización de clientes, con su historial de compras.",
  },
  {
    nombre: "Productos y stock",
    detalle: "ABM de productos, precios, existencias y punto de reposición.",
  },
  {
    nombre: "Compras y ventas",
    detalle: "Registro de operaciones y su impacto automático sobre el stock.",
  },
  {
    nombre: "Administración de usuarios",
    detalle: "Usuarios del sistema, roles y permisos.",
  },
  {
    nombre: "Sugerencia de reposición (IA)",
    detalle: "Propone qué comprar y cuánto, anticipando el quiebre de stock.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="text-sm font-medium uppercase tracking-widest text-slate-500">
        SIMAS 2026 · team grupo21
      </p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight">ERP con IA</h1>
      <p className="mt-4 text-lg text-slate-600 dark:text-slate-400">
        Trabajo Práctico Integrador. Proyecto inicializado — los módulos se
        implementan a partir del modelo de datos.
      </p>

      <ul className="mt-10 space-y-3">
        {MODULOS.map((modulo) => (
          <li
            key={modulo.nombre}
            className="rounded-lg border border-slate-200 p-4 dark:border-slate-800"
          >
            <h2 className="font-semibold">{modulo.nombre}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              {modulo.detalle}
            </p>
          </li>
        ))}
      </ul>
    </main>
  );
}
