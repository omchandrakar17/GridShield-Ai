/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a5f',
        },
        // Control-room palette used by the landing page and app shell.
        ink: {
          DEFAULT: '#0A1420',
          800: '#101E33',
          700: '#152840',
          600: '#1E344F',
          400: '#3B5372',
          300: '#6B85A3',
        },
        amber: {
          DEFAULT: '#F5A623',
          400: '#F7B84D',
          500: '#F5A623',
          600: '#D98A0E',
        },
        current: {
          DEFAULT: '#2DD4BF',
          400: '#5EE6D5',
          500: '#2DD4BF',
          600: '#1FAE9C',
        },
        // Dark-theme remap of Tailwind's default gray scale. Existing pages already
        // use gray-50..900 for backgrounds/borders/text; overriding the scale here
        // (rather than editing every page) flips the whole app to the dark
        // control-room theme used by the landing page and sidebar.
        gray: {
          50: '#0A1420',
          100: '#101E33',
          200: '#1E344F',
          300: '#2A4260',
          400: '#6B85A3',
          500: '#8CA3BF',
          600: '#AEC0D6',
          700: '#D3DEEA',
          800: '#EAF0F6',
          900: '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
