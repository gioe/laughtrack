/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [{
      protocol: 'https',
      hostname: 'laughtrack.b-cdn.net',
    }, ],
  }
};

export default nextConfig
