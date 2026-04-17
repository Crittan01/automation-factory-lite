import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'var(--ink)',
        haze: 'var(--haze)',
        accent: 'var(--accent)',
        aqua: 'var(--aqua)',
        ember: 'var(--ember)'
      },
      boxShadow: {
        glow: '0 10px 45px rgba(2, 132, 199, 0.2)'
      }
    },
  },
  plugins: [],
};

export default config;
