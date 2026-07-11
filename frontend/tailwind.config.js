/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 背景层级（从深到浅）
        base: '#070b14',
        surface: '#0d1420',
        elevated: '#141d2c',
        hover: '#1a2536',
        active: '#1f2d40',

        // 边框
        line: '#1a2535',
        'line-soft': '#2a3a50',
        'line-strong': '#3a4a60',

        // 文字
        t1: '#e6edf3',
        t2: '#9fb0c3',
        t3: '#5d6b7e',
        t4: '#3d4858',

        // 强调色 - 金色
        gold: '#f0b90b',
        'gold-light': '#fcd535',
        'gold-dark': '#c99700',

        // 强调色 - 青色
        'cyan-glow': '#00d4ff',
        'cyan-soft': '#5ce7ff',
        'cyan-dark': '#0099cc',

        // 辅助强调
        azure: '#3b82f6',

        // 功能色
        success: '#00c853',
        danger: '#ff4757',
        warning: '#ffa726',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        sans: ['"Noto Sans SC"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'glow-gold': '0 0 20px rgba(240, 185, 11, 0.15)',
        'glow-cyan': '0 0 20px rgba(0, 212, 255, 0.15)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
