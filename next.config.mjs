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
      }
    ],
  },
  logging: {
    fetches: {
      fullUrl: true,
    },
  }
};

export default nextConfig
