# LaughTrack

Comedy show discovery platform — find clubs, comedians, and shows near you.

This is a monorepo containing two apps:

## Apps

| App | Path | Description |
|-----|------|-------------|
| `web` | [`apps/web`](apps/web/) | Next.js web application |
| `scraper` | [`apps/scraper`](apps/scraper/) | Python show scraper |

## Getting Started

### Web App

```bash
cd apps/web
npm install
npm run dev
```

### Scraper

```bash
cd apps/scraper
make install
make test
```

## Structure

```
laughtrack/
├── apps/
│   ├── web/       # Next.js 15 app (TypeScript, Tailwind, Prisma)
│   └── scraper/   # Python scraper (see apps/scraper/README.md)
├── .github/
│   └── workflows/ # CI for both apps
└── README.md
```
