import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

// Color definitions
const baseColors = {
    transparent: "transparent",
    current: "currentColor",
    white: "#ffffff",
    purple: "#3f3cbb",
    midnight: "#121063",
    metal: "#565584",
    tahiti: "#3ab7bf",
    silver: "#ecebff",
    "bubble-gum": "#ff77e9",
    bermuda: "#78dcca",
};

// Surface + text tokens mirrored from the iOS design system
// (ios/Sources/LaughTrackBridge/LaughTrackTheme.swift). Keep the two in sync:
// canvas/surface scale, warm off-white text, copper accent family.
// For text, use the existing theme tokens (they already match iOS):
// text-foreground (#FAF1E8-equivalent warm cream) and text-muted-foreground
// (70% gray = iOS textSecondary #B3B3B3).
const systemColors = {
    canvas: "#121212",
    surface: {
        DEFAULT: "#181818",
        muted: "#1F1F1F",
        elevated: "#282828",
        skeleton: "#322921",
    },
    "accent-strong": "#CD6837",
    "accent-muted": "#6C4527",
    highlight: "#5F472F",
};

const brandColors = {
    "navy-blue": "#003366",
    "rose-gold": "#B76E79",
    "silver-gray": "#C0C0C0",
    shark: "#1C232A",
    "brown-rust": "#B95D3B",
    "sandy-brown": "#F6916C",
    kelp: "#474838",
    ivory: "#FFFFF0",
    paarl: "#A96030",
    cedar: "#361E14",
    "coconut-cream": "rgb(var(--coconut-cream-rgb) / <alpha-value>)",
    locust: "#acae89",
    "pine-tree": "#232604",
    skeptic: "#9eb4aa",
    "ecru-white": "#fafaf0",
    juniper: "#72908e",
    "tax-break": "#4c6b73",
    madison: "#2f4858",
    "american-silver": "#ced9cb",
    "midnight-blue": "#003366",
    copper: "#B87333",
    "copper-dark": "#7A3F16",
    "copper-bright": "#CD6837",
    "cedar-dark": "#2D1810",
    "soft-charcoal": "#4A4A4A",
    champagne: "#F7E7CE",
};

const themeColors = {
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    card: {
        DEFAULT: "hsl(var(--card))",
        foreground: "hsl(var(--card-foreground))",
    },
    popover: {
        DEFAULT: "hsl(var(--popover))",
        foreground: "hsl(var(--popover-foreground))",
    },
    primary: {
        DEFAULT: "hsl(var(--primary))",
        foreground: "hsl(var(--primary-foreground))",
    },
    secondary: {
        DEFAULT: "hsl(var(--secondary))",
        foreground: "hsl(var(--secondary-foreground))",
    },
    muted: {
        DEFAULT: "hsl(var(--muted))",
        foreground: "hsl(var(--muted-foreground))",
    },
    accent: {
        DEFAULT: "hsl(var(--accent))",
        foreground: "hsl(var(--accent-foreground))",
    },
    destructive: {
        DEFAULT: "hsl(var(--destructive))",
        foreground: "hsl(var(--destructive-foreground))",
    },
    border: "hsl(var(--border))",
    input: "hsl(var(--input))",
    ring: "hsl(var(--ring))",
    chart: {
        "1": "hsl(var(--chart-1))",
        "2": "hsl(var(--chart-2))",
        "3": "hsl(var(--chart-3))",
        "4": "hsl(var(--chart-4))",
        "5": "hsl(var(--chart-5))",
    },
};

// Typography system:
//   font-chivo      → hero/page-level display headings (h1 in hero, login, auth modals)
//   font-urbanist-bold → UI headings and entity names (card titles, section headings, stat values)
//   font-dmSans     → all body text, descriptions, labels, metadata, navigation
const fonts = {
    sans: ["var(--font-dmSans)", "sans-serif"],
    "urbanist-bold": ["var(--font-urbanist)", "sans-serif"],
    bebas: "var(--font-bebas)",
    oswald: "var(--font-oswald)",
    fjalla: "var(--font-fjalla)",
    dmSans: "var(--font-dmSans)",
    chivo: "var(--font-chivo)",
    inter: "var(--font-inter)",
    outfit: "var(--font-outfit)",
};

const config: Config = {
    darkMode: ["class"],
    relative: true,
    content: [
        "./ui/components/**/*.{js,ts,jsx,tsx}",
        "./ui/pages/**/*.{js,ts,jsx,tsx}",
        "./ui/util/**/*.{js,ts,jsx,tsx}",
        "./app/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        screens: {
            "2xs": { min: "300px" },
            xs: { max: "575px" }, // Mobile (iPhone 3 - iPhone XS Max).
            sm: { min: "576px", max: "897px" }, // Mobile (matches max: iPhone 11 Pro Max landscape @ 896px).
            md: { min: "898px", max: "1199px" }, // Tablet (matches max: iPad Pro @ 1112px).
            lg: { min: "1200px" }, // Desktop smallest.
            xl: { min: "1259px" }, // Desktop wide.
            "2xl": { min: "1359px" }, // Desktop widescreen.
        },
        extend: {
            // Typography scale:
            //   Semantic tokens that extend (not replace) Tailwind's default font-size
            //   utilities (text-xs, text-sm, text-base, text-lg, text-xl, text-2xl, …).
            //   Prefer these tokens over ad-hoc text-[Xpx] arbitrary values.
            //
            //   text-caption  13px  badges, chips, metadata, helper text
            //   text-body     16px  default body text, buttons, labels
            //   text-lead     18px  prose, larger body, secondary info
            //   text-h3       22px  card titles, entity names, subheadings
            //   text-h2       26px  section headers, modal titles
            //   text-h1       32px  page titles
            //   text-display  40px  home-page displays, about-page stats
            //   text-hero     48px  empty-state grid titles, hero marks
            fontSize: {
                caption: "13px",
                body: "16px",
                lead: "18px",
                h3: "22px",
                h2: "26px",
                h1: "32px",
                display: "40px",
                hero: "48px",
            },
            spacing: {
                "18": "4.5rem",
                "22": "5.5rem",
                "72": "18rem",
                "84": "21rem",
                "96": "24rem",
            },
            keyframes: {
                pulse: {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.5" },
                },
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { transform: "translateY(10px)", opacity: "0" },
                    "100%": { transform: "translateY(0)", opacity: "1" },
                },
                shimmer: {
                    "0%": { backgroundPosition: "200% 0" },
                    "100%": { backgroundPosition: "-200% 0" },
                },
            },
            animation: {
                pulse: "pulse 2s ease-in-out infinite",
                fadeIn: "fadeIn 0.3s ease-in-out",
                slideUp: "slideUp 0.4s ease-out",
                shimmer: "shimmer 1.4s infinite linear",
            },
            fontFamily: fonts,
            colors: {
                ...baseColors,
                ...systemColors,
                ...brandColors,
                ...themeColors,
            },
            // border-subtle / border-strong — faint hairlines from the iOS
            // border scale (#2A2A2A / #3A3A3A).
            borderColor: {
                subtle: "#2A2A2A",
                strong: "#3A3A3A",
            },
            ringColor: {
                subtle: "#2A2A2A",
                strong: "#3A3A3A",
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
                card: "16px",
                "hero-panel": "28px",
            },
            // Elevation scale mirrored from iOS LaughTrackTheme shadows
            // (card / hero / floating). Prefer these over ad-hoc shadow-*.
            boxShadow: {
                card: "0 4px 10px rgb(0 0 0 / 0.08)",
                floating: "0 6px 14px rgb(0 0 0 / 0.12)",
                hero: "0 10px 18px rgb(0 0 0 / 0.18)",
            },
        },
    },
    variants: {
        fill: ["hover", "focus"],
    },
    plugins: [forms],
};

export default config;
