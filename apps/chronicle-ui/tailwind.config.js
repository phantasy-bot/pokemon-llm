/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Space Mono"', 'monospace'],
        display: ['"Space Grotesk"', 'sans-serif'],
      },
      colors: {
        paper: {
          DEFAULT: '#FDFBF7',
          dark: '#F2F0E9',
        },
        ink: {
          DEFAULT: '#18181B',
          light: '#52525B',
        }
      },
      boxShadow: {
        'brutal': '4px 4px 0px 0px rgba(0,0,0,1)',
        'brutal-sm': '2px 2px 0px 0px rgba(0,0,0,1)',
      }
    },
  },
  plugins: [],
}
