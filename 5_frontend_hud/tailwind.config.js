/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        space: {
          900: '#0B0F19',
          800: '#111827',
          700: '#1A2033',
          600: '#1E2A44',
          500: '#263352',
        },
        status: {
          normal:   '#10B981', // Emerald-500
          warning:  '#F59E0B', // Amber-500
          critical: '#EF4444', // Red-500
          dim:      '#6B7280', // Gray-500
        },
        accent: {
          blue:  '#3B82F6',
          cyan:  '#06B6D4',
          white: '#F8FAFC',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      animation: {
        pulse_fast: 'pulse 1s cubic-bezier(0.4,0,0.6,1) infinite',
      }
    }
  },
  plugins: [],
}
