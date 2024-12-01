import withPlaiceholder from "@plaiceholder/next";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // rewrites: async () => {
  //   return [{
  //     source: '/api/:path*',
  //     destination: process.env.NODE_ENV === 'development' ?
  //       'http://127.0.0.1:5328/api/:path*' : '/api/',
  //   }, ]
  // },
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
  // Works, but need to replace with serverExternalPackages later
  webpack: (
    config, {},
  ) => {
    // add externals
    config.externals = config.externals || [];
    config.externals.push(
      "playwright-extra",
      "puppeteer-extra-plugin-stealth"
    );
    config.resolve.fallback = {
      fs: false,
      path: false
    };


    return config;
  }
};

export default withPlaiceholder(nextConfig);
