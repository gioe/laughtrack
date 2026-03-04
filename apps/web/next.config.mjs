/** @type {import('next').NextConfig} */
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

export default nextConfig
