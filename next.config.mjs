/** @type {import('next').NextConfig} */
const nextConfig = {
  // Works, but need to replace with serverExternalPackages later
  webpack: (
    config, {
      buildId,
      dev,
      isServer,
      defaultLoaders,
      nextRuntime,
      webpack
    },
  ) => {
    // add externals
    config.externals = config.externals || [];
    config.externals.push(
      "playwright-extra",
      "puppeteer-extra-plugin-stealth"
    );

    return config;
  }
};

export default nextConfig;
