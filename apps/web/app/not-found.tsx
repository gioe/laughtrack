import Link from "next/link";
import { Mic } from "lucide-react";
import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Button } from "@/ui/components/ui/button";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

// Comedy-club "empty stage" treatment, matching the show-card Brick & Spotlight
// aesthetic: warm near-black surface, faint brick masonry, a warm spotlight from
// above, and a lone mic. CSS-only staggered reveal so this stays a server
// component (it awaits auth for the navbar). Respects prefers-reduced-motion via
// the global reduced-motion rule in globals.css.
const BRICK_TEXTURE =
    "repeating-linear-gradient(0deg, rgba(255,255,255,0.045) 0px, rgba(255,255,255,0.045) 1px, transparent 1px, transparent 24px)," +
    "repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 48px)";
const SPOTLIGHT =
    "radial-gradient(70% 60% at 50% -5%, rgba(247,231,206,0.16), rgba(184,115,51,0.06) 42%, transparent 72%)";
const FLOOR_POOL =
    "radial-gradient(60% 90% at 50% 100%, rgba(184,115,51,0.12), transparent 70%)";

const reveal = (delayMs: number) => ({
    animation: "slideUp 0.55s ease-out both",
    animationDelay: `${delayMs}ms`,
});

const QUICK_LINKS = [
    { label: "Shows", href: "/show/search" },
    { label: "Comedians", href: "/comedian/search" },
    { label: "Clubs", href: "/club/search" },
    { label: "Podcasts", href: "/podcast/search" },
];

export default async function NotFound() {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <div className="flex flex-col min-h-screen">
                <Navbar currentUser={session?.profile} />
                <main
                    id="main-content"
                    className="relative flex flex-1 flex-col items-center justify-center bg-[#161210] px-4 py-20 text-center"
                >
                    {/* Atmosphere: brick wall + spotlight from above + floor
                        pool. Clipping lives on this decorative wrapper (not the
                        main) so it never crops content on short viewports. */}
                    <div
                        aria-hidden="true"
                        className="pointer-events-none absolute inset-0 overflow-hidden"
                    >
                        <div
                            className="absolute inset-0 opacity-[0.05]"
                            style={{ backgroundImage: BRICK_TEXTURE }}
                        />
                        <div
                            className="absolute inset-0"
                            style={{ background: SPOTLIGHT }}
                        />
                        <div
                            className="absolute inset-x-0 bottom-0 h-1/3"
                            style={{ background: FLOOR_POOL }}
                        />
                    </div>

                    <div className="relative z-[1] flex max-w-xl flex-col items-center gap-5">
                        <Mic
                            aria-hidden="true"
                            strokeWidth={1.25}
                            className="h-12 w-12 text-champagne/40"
                            style={reveal(0)}
                        />

                        <span
                            className="font-oswald text-sm font-medium uppercase tracking-[0.35em] text-copper-bright"
                            style={reveal(70)}
                        >
                            Tough crowd
                        </span>

                        <p
                            className="font-bebas leading-[0.82] text-foreground text-[7rem] sm:text-[10rem]"
                            style={{
                                ...reveal(140),
                                textShadow: "0 0 45px rgba(205,104,55,0.35)",
                            }}
                        >
                            404
                        </p>

                        <h1
                            className="font-gilroy-bold text-2xl font-bold text-foreground sm:text-3xl"
                            style={reveal(210)}
                        >
                            This page bombed.
                        </h1>

                        <p
                            className="max-w-md font-dmSans text-base leading-relaxed text-foreground/65"
                            style={reveal(280)}
                        >
                            The page you&apos;re looking for got cut from the
                            set — it moved, retired, or never made it past the
                            open mic. Let&apos;s get you back to the good stuff.
                        </p>

                        <div style={reveal(350)}>
                            <Button asChild variant="roundedShimmer">
                                <Link href="/">Back to the show</Link>
                            </Button>
                        </div>

                        <nav
                            aria-label="Browse LaughTrack"
                            className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-2 font-oswald text-sm uppercase tracking-[0.18em]"
                            style={reveal(420)}
                        >
                            {QUICK_LINKS.map((link, index) => (
                                <span key={link.href} className="contents">
                                    {index > 0 && (
                                        <span
                                            aria-hidden="true"
                                            className="text-copper/40"
                                        >
                                            ·
                                        </span>
                                    )}
                                    <Link
                                        href={link.href}
                                        className="text-foreground/70 transition-colors hover:text-copper-bright focus-visible:text-copper-bright focus-visible:outline-none"
                                    >
                                        {link.label}
                                    </Link>
                                </span>
                            ))}
                        </nav>
                    </div>
                </main>
                <FooterComponent />
            </div>
        </StyleContextProvider>
    );
}
