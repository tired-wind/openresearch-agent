import type { NextConfig } from 'next';
const config: NextConfig = {
  async rewrites() { return [{source:'/api/:path*',destination:'http://127.0.0.1:8018/api/:path*'}]; },
  poweredByHeader: false,
};
export default config;
