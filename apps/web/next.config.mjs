import { withSentryConfig } from '@sentry/nextjs';

/** @type {import('next').NextConfig} */
// Note: DATABASE_URL and DIRECT_URL are intentionally omitted from the `env` block.
// They are server-side-only credentials read directly via process.env in lib/db.ts
// and prisma/schema.prisma. Listing them here would expose them in the client bundle.
const nextConfig = {
  images: {
    minimumCacheTTL: 0,
    remotePatterns: [{
        protocol: 'https',
        port: '',
        pathname: '/assets/**',
        hostname: 'laughtrack.b-cdn.net',
      },
      {
        protocol: 'https',
        port: '',
        pathname: '/comedians/**',
        hostname: 'laughtrack.b-cdn.net',
      },
      {
        protocol: 'https',
        port: '',
        pathname: '/clubs/**',
        hostname: 'laughtrack.b-cdn.net',
      },
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
        port: '',
        pathname: '/a/**',
      }
    ],
  },
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
  experimental: {
    serverActions: {
      allowedOrigins: ['laughtrack.b-cdn.net'],
    },
  },
};

export default withSentryConfig(nextConfig, {
    silent: true,
    disableLogger: true,
})
