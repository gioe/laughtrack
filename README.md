# LaughTrack

Comedy show discovery platform — find clubs, comedians, and shows near you.

This is a monorepo containing three apps:

## Apps

| App | Path | Description |
|-----|------|-------------|
| `web` | [`apps/web`](apps/web/) | Next.js web application |
| `scraper` | [`apps/scraper`](apps/scraper/) | Python show scraper |
| `ios` | [`ios`](ios/) | Native SwiftUI iOS app (consumes the web app's `/api/v1` contract) |

## Getting Started

### Web App

```bash
cd apps/web
cp .env.example .env.local   # fill in your secrets
npm install
npm run dev
```

See [`apps/web/.env.example`](apps/web/.env.example) for a description of all required environment variables.

### Scraper

```bash
cd apps/scraper
make install
make test
```

### iOS App

```bash
cd ios
swift build          # build all targets
swift test           # pure-Swift unit tests (macOS)
```

See [`ios/CLAUDE.md`](ios/CLAUDE.md) for the simulator test flow, OpenAPI client regeneration, and the ios-libs bridge architecture.

## Structure

```
laughtrack/
├── apps/
│   ├── web/       # Next.js 15 app (TypeScript, Tailwind, Prisma)
│   └── scraper/   # Python scraper (see apps/scraper/README.md)
├── ios/           # SwiftUI iOS app (see ios/CLAUDE.md)
├── docs/          # Cross-cutting design + ops docs
├── .github/
│   └── workflows/ # CI for all apps
├── AGENTS.md      # Agent/Claude working conventions
├── CLAUDE.md      # Project conventions (points at the tusk conventions DB)
└── README.md
```
