import { PrismaClient } from "@prisma/client";

// En desarrollo Next.js recarga los módulos en caliente; sin este singleton se
// abriría una conexión nueva a Postgres en cada recarga hasta agotar el pool.
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db;
