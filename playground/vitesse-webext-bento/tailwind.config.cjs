/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,vue,ts}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'SF Pro Display',
          'SF Pro Text',
          'ui-sans-serif',
          'system-ui',
          'sans-serif',
        ],
      },
      boxShadow: {
        glass: '0 20px 60px rgba(15, 23, 42, 0.18)',
        card: '0 10px 30px rgba(15, 23, 42, 0.16)',
      },
      colors: {
        ink: '#111827',
      },
      backdropBlur: {
        xl: '24px',
      },
      backgroundImage: {
        grain: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.12) 1px, transparent 0)',
      },
    },
  },
  plugins: [],
}
