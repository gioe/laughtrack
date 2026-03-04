const DEFAULT_ALLOWED_ORIGINS = ['laughtrack.b-cdn.net']

function getAllowedOrigins(): string[] {
    const env = process.env.CORS_ALLOWED_ORIGINS
    if (!env) return DEFAULT_ALLOWED_ORIGINS
    if (env === '*') return ['*']
    return env.split(',').map((o) => o.trim()).filter(Boolean)
}

export function getCorsHeaders(origin: string | null): Record<string, string> {
    const allowedOrigins = getAllowedOrigins()
    const allowAll = allowedOrigins.includes('*')

    let allowOrigin: string
    if (allowAll) {
        allowOrigin = '*'
    } else if (origin && allowedOrigins.includes(origin)) {
        allowOrigin = origin
    } else {
        allowOrigin = allowedOrigins[0] ?? ''
    }

    return {
        'Access-Control-Allow-Origin': allowOrigin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '86400',
    }
}
