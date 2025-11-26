/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove standalone for Render - it handles Node.js natively
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Allow images from any domain (for future use)
  images: {
    remotePatterns: [],
  },
};

module.exports = nextConfig;