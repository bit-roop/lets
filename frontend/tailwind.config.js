/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#0B5FA5',
          dark: '#083E6E',
          darker: '#062B4D',
          tint: '#EAF3FC',
          border: '#CFE0F2',
        },
        ink: {
          900: '#111827',
          700: '#374151',
          500: '#6B7280',
          300: '#D1D5DB',
        },
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
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        serif: ['Merriweather', 'Georgia', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 1px rgba(15, 23, 42, 0.04)',
        cardHover: '0 4px 12px rgba(15, 23, 42, 0.08)',
      },
      borderRadius: {
        xl: '0.875rem',
      },
    },
  },
  plugins: [],
}