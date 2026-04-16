import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.popo.musinsa.pricewatcher',
  appName: 'Musinsa Price Watcher',
  webDir: 'web',
  server: {
    url: 'https://musinsa-price-watcher.onrender.com',
    cleartext: false,
  },
  ios: {
    contentInset: 'automatic',
  },
};

export default config;
