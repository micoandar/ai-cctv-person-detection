/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#070A11',
          900: '#0A0F1A',
          800: '#0D1220',
          700: '#131A2A',
          600: '#1B2436',
          500: '#26314A',
        },
        neon: {
          DEFAULT: '#22D3EE',
          soft: '#0891B2',
          green: '#4ADE80',
          red: '#F87171',
          amber: '#FBBF24',
        },
      },
      boxShadow: {
        soft: '0 10px 30px -12px rgba(0,0,0,0.65)',
        glow: '0 0 0 1px rgba(34,211,238,0.25), 0 0 24px -6px rgba(34,211,238,0.45)',
      },
      keyframes: {
        livePulse: {
          '0%, 100%': { opacity: 1, transform: 'scale(1)' },
          '50%': { opacity: 0.35, transform: 'scale(0.82)' },
        },
        fadeUp: {
          '0%': { opacity: 0, transform: 'translateY(6px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      animation: {
        'live-pulse': 'livePulse 1.4s ease-in-out infinite',
        'fade-up': 'fadeUp 0.25s ease-out',
      },
    },
  },
  plugins: [],
}