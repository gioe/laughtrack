import { PrismaClient } from '@prisma/client'
import { PrismaNeon } from '@prisma/adapter-neon'
import { Pool } from '@neondatabase/serverless'

// Create a singleton instance of the Prisma client
const globalForPrisma = globalThis as unknown as {
    prisma: PrismaClient | undefined
}

// Initialize the Neon connection pool
const connectionString = process.env.DATABASE_URL
if (!connectionString) {
    throw new Error('DATABASE_URL environment variable is not set')
}

// Create the Prisma client with the Neon adapter
const prismaClientSingleton = () => {
    const neon = new Pool({ connectionString })
    const adapter = new PrismaNeon(neon)

    return new PrismaClient({
        adapter,
        log: process.env.NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
    })
}

// In development, store the Prisma client in the global scope to prevent multiple instances
if (process.env.NODE_ENV !== 'production') {
    if (!globalForPrisma.prisma) {
        globalForPrisma.prisma = prismaClientSingleton()
    }
}

export const prisma = process.env.NODE_ENV === 'production'
    ? prismaClientSingleton()
    : globalForPrisma.prisma!

export const db = prisma
