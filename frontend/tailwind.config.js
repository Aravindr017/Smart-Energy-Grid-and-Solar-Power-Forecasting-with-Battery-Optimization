/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        navy: {
          50: '#eef3f8',
          100: '#d5e0eb',
          700: '#1b3a57',
          800: '#132a40',
          900: '#0b1f33',
          950: '#071525',
        },
        solar: {
          50: '#fffbeb',
          100: '#fef3c7',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
        charge: '#059669',
        discharge: '#2563eb',
        import: '#ea580c',
        export: '#0d9488',
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.04)',
      },
    },
  },
  plugins: [],
};
