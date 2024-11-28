import withPlaiceholder from "@plaiceholder/next";

/** @type {import('next').NextConfig} */
const nextConfig = {
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
