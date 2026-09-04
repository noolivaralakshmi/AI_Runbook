/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        dark: { 800: '#1a1a2e', 900: '#0f0f1a' },
        brand: { 500: '#e63946', 600: '#c1121f' }
      }
    }
  },
  plugins: [],
}
