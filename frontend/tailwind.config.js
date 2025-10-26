/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
          text: '#e2e8f0',
          muted: '#94a3b8',
        },
        accent: {
          primary: '#38bdf8',
          secondary: '#818cf8',
          success: '#34d399',
          warning: '#fbbf24',
          danger: '#f87171',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(56, 189, 248, 0.5)' },
          '50%': { boxShadow: '0 0 20px rgba(56, 189, 248, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}