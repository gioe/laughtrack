import { PrismaClient } from "@prisma/client";
import { PrismaNeon } from "@prisma/adapter-neon";
import { Pool } from "@neondatabase/serverless";

// Create a singleton instance of the Prisma client
const globalForPrisma = globalThis as unknown as {
    prisma: PrismaClient | undefined;
};

// Create the Prisma client with the Neon adapter
const prismaClientSingleton = () => {
    const neon = new Pool({ connectionString: process.env.DATABASE_URL });
    const adapter = new PrismaNeon(neon);

    return new PrismaClient({
        adapter,
        log:
            process.env.NODE_ENV === "development"
                ? ["query", "info", "warn", "error"]
                : ["error"],
    });
};

// In development, store the Prisma client in the global scope to prevent multiple instances
if (process.env.NODE_ENV !== "production") {
    if (!globalForPrisma.prisma) {
        globalForPrisma.prisma = prismaClientSingleton();
    }
}

export const prisma =
    process.env.NODE_ENV === "production"
        ? prismaClientSingleton()
        : globalForPrisma.prisma!;

export const db = prisma;
