const DEFAULT_ALLOWED_ORIGINS = ['laughtrack.b-cdn.net']

// Memoize at module load — env vars are static after startup
const ALLOWED_ORIGINS: string[] = (() => {
    const env = process.env.CORS_ALLOWED_ORIGINS
    if (!env) return DEFAULT_ALLOWED_ORIGINS
    if (env === '*') return ['*']
    return env.split(',').map((o) => o.trim()).filter(Boolean)
})()

export function getCorsHeaders(origin: string | null): Record<string, string> {
    const allowAll = ALLOWED_ORIGINS.includes('*')

    const headers: Record<string, string> = {
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '86400',
        'Vary': 'Origin',
    }

    if (allowAll) {
        headers['Access-Control-Allow-Origin'] = '*'
    } else if (origin && ALLOWED_ORIGINS.includes(origin)) {
        headers['Access-Control-Allow-Origin'] = origin
    }
    // Disallowed origin: omit Access-Control-Allow-Origin entirely

    return headers
}
