import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { withSentryConfig } from '@sentry/nextjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
// Note: DATABASE_URL and DIRECT_URL are intentionally omitted from the `env` block.
// They are server-side-only credentials read directly via process.env in lib/db.ts
// and prisma/schema.prisma. Listing them here would expose them in the client bundle.
const nextConfig = {
  // Pin workspace root to apps/web/ so Next.js doesn't infer it from a stray
  // lockfile in a parent directory (e.g. ~/package-lock.json).
  outputFileTracingRoot: __dirname,
  async redirects() {
    return [
      {
        source: '/comedians',
        destination: '/comedian/search',
        permanent: true,
      },
      {
        source: '/shows',
        destination: '/show/search',
        permanent: true,
      },
      {
        source: '/clubs',
        destination: '/club/search',
        permanent: true,
      },
      {
        source: '/podcasts',
        destination: '/podcast/search',
        permanent: true,
      },
    ];
  },
  images: {
    minimumCacheTTL: 0,
    qualities: [75, 90],
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
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
      },
      // Podcast artwork is sourced from feed-owned CDN hosts.
      {
        protocol: 'https',
        hostname: '**',
        port: '',
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
    removeDebugLogging: true,
    tunnelRoute: '/monitoring',
})
