/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        koyfin: {
          bg: '#f0f1f3',
          card: '#ffffff',
          hover: '#f7f8fa',
          border: '#e2e4e8',
          green: '#00a562',
          red: '#e5484d',
          amber: '#d97b0e',
          text: '#1a1a2e',
          muted: '#6b7280',
        },
      },
    },
  },
  plugins: [],
}
