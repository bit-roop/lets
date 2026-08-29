/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: '#0B2545',
          navyLight: '#134074',
          gold: '#C59B27',
          goldLight: '#E8CA65',
          slate: '#0F172A',
          slateLight: '#334155',
          muted: '#64748B',
          surface: '#FFFFFF',
          canvas: '#F8FAFC',
          border: '#CBD5E1',
          borderLight: '#E2E8F0',
        },
        status: {
          applicable: '#166534',
          applicableBg: '#DCFCE7',
          applicableBorder: '#86EFAC',
          notApplicable: '#475569',
          notApplicableBg: '#F1F5F9',
          notApplicableBorder: '#CBD5E1',
          unknown: '#9A3412',
          unknownBg: '#FFEDD5',
          unknownBorder: '#FDBA74',
          conflict: '#991B1B',
          conflictBg: '#FEE2E2',
          conflictBorder: '#FCA5A5',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        serif: ['Merriweather', 'Georgia', 'serif'],
        mono: ['Consolas', 'Courier New', 'monospace'],
      }
    },
  },
  plugins: [],
}
