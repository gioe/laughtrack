type SearchSkeletonVariant = "club" | "comedian" | "show";

const shimmer =
    "bg-gradient-to-r from-stone-200 via-stone-100 to-stone-200 bg-[length:400%_100%] animate-shimmer";
const darkShimmer =
    "bg-gradient-to-r from-white/12 via-white/24 to-white/12 bg-[length:400%_100%] animate-shimmer";

interface SkeletonBlockProps {
    className: string;
    dark?: boolean;
}

export function SkeletonBlock({ className, dark = false }: SkeletonBlockProps) {
    return (
        <div
            className={`${dark ? darkShimmer : shimmer} ${className}`}
            aria-hidden="true"
        />
    );
}

export function SearchPageSkeleton({
    variant,
}: {
    variant: SearchSkeletonVariant;
}) {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <SearchHeaderSkeleton variant={variant} />
            <SearchFilterBarSkeleton variant={variant} />
            {variant === "show" ? (
                <ShowResultsSkeleton />
            ) : (
                <EntityGridSkeleton variant={variant} />
            )}
        </main>
    );
}

function SearchHeaderSkeleton({ variant }: { variant: SearchSkeletonVariant }) {
    const container =
        variant === "club"
            ? "bg-gradient-to-r from-cedar to-copper"
            : "bg-gradient-to-br from-cedar to-copper";

    return (
        <header className={`px-4 py-16 text-center md:py-20 ${container}`}>
            <SkeletonBlock
                dark
                className="mx-auto mb-3 h-9 w-56 rounded-md sm:h-10 md:h-12"
            />
            <SkeletonBlock dark className="mx-auto mb-2 h-5 w-72 rounded-md" />
            <SkeletonBlock dark className="mx-auto h-5 w-28 rounded-md" />
        </header>
    );
}

function SearchFilterBarSkeleton({
    variant,
}: {
    variant: SearchSkeletonVariant;
}) {
    const hasExtraControl = variant !== "show";

    return (
        <div className="sticky top-0 z-20 w-full border-b border-black/5 bg-coconut-cream">
            <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
                    <SkeletonBlock className="h-11 min-w-0 rounded-lg lg:flex-1" />
                    <div className="flex flex-wrap items-center gap-3 lg:shrink-0">
                        <SkeletonBlock className="h-9 w-36 rounded-md" />
                        <SkeletonBlock className="h-9 w-24 rounded-md" />
                        {hasExtraControl && (
                            <SkeletonBlock className="h-8 w-24 rounded-full" />
                        )}
                        <SkeletonBlock className="hidden h-5 w-20 rounded-md sm:block" />
                    </div>
                </div>
            </div>
        </div>
    );
}

function EntityGridSkeleton({ variant }: { variant: "club" | "comedian" }) {
    return (
        <section className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                {Array.from({ length: 10 }).map((_, index) => (
                    <article
                        key={index}
                        className="h-full rounded-xl border border-black/5 bg-white/70 p-4 shadow-sm"
                    >
                        <SkeletonBlock
                            className={
                                variant === "club"
                                    ? "mb-4 aspect-video w-full rounded-xl"
                                    : "mx-auto mb-4 aspect-square w-full rounded-xl"
                            }
                        />
                        <SkeletonBlock className="mx-auto mb-3 h-6 w-3/4 rounded-md" />
                        <SkeletonBlock className="mx-auto mb-3 h-4 w-2/3 rounded-md" />
                        <SkeletonBlock className="mx-auto h-6 w-32 rounded-full" />
                    </article>
                ))}
            </div>
        </section>
    );
}

function ShowResultsSkeleton() {
    return (
        <section className="grid grid-cols-1 gap-y-6 px-4 py-8 sm:gap-y-8 sm:px-6 md:gap-y-10 md:px-8">
            {Array.from({ length: 4 }).map((_, index) => (
                <article
                    key={index}
                    className="relative w-full overflow-hidden rounded-xl border border-copper/10 bg-gradient-to-br from-stone-50 to-coconut-cream/45 p-4 shadow-sm sm:p-6"
                >
                    <div className="relative flex flex-col gap-4 lg:flex-row">
                        <div className="flex flex-1 flex-col gap-4 lg:w-[35%]">
                            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                                <div className="flex-1 space-y-3">
                                    <SkeletonBlock className="h-7 w-3/4 rounded-md" />
                                    <SkeletonBlock className="h-4 w-1/2 rounded-md" />
                                    <SkeletonBlock className="h-4 w-2/3 rounded-md" />
                                </div>
                                <SkeletonBlock className="h-11 w-32 rounded-full" />
                            </div>
                            <div className="space-y-2 lg:hidden">
                                <SkeletonBlock className="h-px w-full rounded-none" />
                                <SkeletonBlock className="min-h-[176px] w-full rounded-lg sm:min-h-[220px]" />
                            </div>
                        </div>
                        <SkeletonBlock className="hidden min-h-[248px] rounded-lg lg:block lg:w-[65%]" />
                    </div>
                </article>
            ))}
        </section>
    );
}

export function HomePageSkeleton() {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <section className="relative min-h-[380px] w-full overflow-hidden bg-cedar sm:min-h-[600px] md:min-h-[700px] lg:min-h-[776px]">
                <div className="absolute inset-0 bg-black/55" />
                <div className="relative mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
                    <div className="mb-14 flex items-center justify-between">
                        <SkeletonBlock dark className="h-10 w-36 rounded-md" />
                        <div className="hidden gap-4 sm:flex">
                            <SkeletonBlock
                                dark
                                className="h-8 w-20 rounded-md"
                            />
                            <SkeletonBlock
                                dark
                                className="h-8 w-20 rounded-md"
                            />
                            <SkeletonBlock
                                dark
                                className="h-8 w-20 rounded-md"
                            />
                        </div>
                    </div>
                    <div className="mx-auto max-w-6xl text-center">
                        <SkeletonBlock
                            dark
                            className="mx-auto mb-6 h-14 w-4/5 max-w-4xl rounded-lg sm:h-16 md:h-20"
                        />
                        <SkeletonBlock
                            dark
                            className="mx-auto mb-10 h-8 w-2/3 max-w-3xl rounded-md"
                        />
                        <div className="mb-10 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3">
                            {Array.from({ length: 6 }).map((_, index) => (
                                <div
                                    key={index}
                                    className="flex min-h-[96px] overflow-hidden rounded-lg border border-white/15 bg-white/12"
                                >
                                    <SkeletonBlock
                                        dark
                                        className="h-auto w-16 flex-none sm:w-24"
                                    />
                                    <div className="flex flex-1 flex-col justify-center gap-2 px-3">
                                        <SkeletonBlock
                                            dark
                                            className="h-4 w-4/5 rounded-md"
                                        />
                                        <SkeletonBlock
                                            dark
                                            className="h-3 w-2/3 rounded-md"
                                        />
                                        <SkeletonBlock
                                            dark
                                            className="h-3 w-1/2 rounded-md"
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                        <SkeletonBlock
                            dark
                            className="mx-auto h-16 w-full max-w-3xl rounded-full"
                        />
                    </div>
                </div>
            </section>

            <HomeComedianSectionSkeleton />
            <HomeShowRailSkeleton />
            <HomeClubRailSkeleton />
        </main>
    );
}

function HomeComedianSectionSkeleton() {
    return (
        <section className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6">
            <SkeletonBlock className="mb-3 h-10 w-80 max-w-full rounded-md" />
            <SkeletonBlock className="mb-8 h-6 w-[32rem] max-w-full rounded-md" />
            <div className="grid grid-cols-1 gap-x-4 gap-y-7 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-8">
                {Array.from({ length: 8 }).map((_, index) => (
                    <div key={index}>
                        <SkeletonBlock className="mb-3 aspect-square w-24 max-w-28 rounded-xl md:w-28 lg:w-full" />
                        <SkeletonBlock className="mb-2 h-5 w-24 rounded-md" />
                        <SkeletonBlock className="h-5 w-20 rounded-full" />
                    </div>
                ))}
            </div>
        </section>
    );
}

function HomeShowRailSkeleton() {
    return (
        <section className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <SkeletonBlock className="mb-2 h-9 w-64 rounded-md" />
                    <SkeletonBlock className="h-5 w-80 max-w-full rounded-md" />
                </div>
                <div className="flex gap-3 self-end sm:self-auto">
                    <SkeletonBlock className="h-9 w-16 rounded-md" />
                    <SkeletonBlock className="h-9 w-20 rounded-md" />
                </div>
            </div>
            <div className="flex gap-4 overflow-hidden py-4 px-2">
                {Array.from({ length: 4 }).map((_, index) => (
                    <article
                        key={index}
                        className="flex h-56 w-[260px] flex-none flex-col gap-3 rounded-xl border border-copper/10 bg-white/70 p-4 sm:w-[300px]"
                    >
                        <div className="flex items-center gap-3">
                            <SkeletonBlock className="h-10 w-10 rounded-full" />
                            <div className="min-w-0 flex-1 space-y-2">
                                <SkeletonBlock className="h-5 w-full rounded-md" />
                                <SkeletonBlock className="h-4 w-2/3 rounded-md" />
                            </div>
                        </div>
                        <SkeletonBlock className="h-4 w-4/5 rounded-md" />
                        <SkeletonBlock className="h-4 w-3/5 rounded-md" />
                        <SkeletonBlock className="mt-auto h-5 w-24 rounded-md" />
                    </article>
                ))}
            </div>
        </section>
    );
}

function HomeClubRailSkeleton() {
    return (
        <section className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div>
                    <SkeletonBlock className="mb-2 h-9 w-52 rounded-md" />
                    <SkeletonBlock className="h-5 w-72 max-w-full rounded-md" />
                </div>
                <div className="flex gap-2 self-end sm:self-auto">
                    <SkeletonBlock className="h-9 w-9 rounded-md" />
                    <SkeletonBlock className="h-9 w-9 rounded-md" />
                </div>
            </div>
            <div className="flex gap-4 overflow-hidden py-4 px-2 md:gap-6">
                {Array.from({ length: 4 }).map((_, index) => (
                    <article
                        key={index}
                        className="w-[280px] max-w-[calc(100vw-2rem)] flex-none rounded-xl border border-black/5 bg-white/70 p-4 shadow-sm sm:w-[320px]"
                    >
                        <SkeletonBlock className="mb-4 aspect-video w-full rounded-xl" />
                        <SkeletonBlock className="mx-auto mb-3 h-6 w-3/4 rounded-md" />
                        <SkeletonBlock className="mx-auto mb-3 h-4 w-2/3 rounded-md" />
                        <SkeletonBlock className="mx-auto h-6 w-32 rounded-full" />
                    </article>
                ))}
            </div>
        </section>
    );
}

export function DetailPageSkeleton() {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                <div className="relative h-52 w-full overflow-hidden rounded-xl bg-gradient-to-br from-stone-600 via-stone-800 to-stone-900 sm:h-64 md:h-80">
                    <SkeletonBlock
                        dark
                        className="absolute inset-0 rounded-none"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                    <div className="absolute bottom-0 left-0 right-0 p-6">
                        <SkeletonBlock
                            dark
                            className="mb-3 h-7 w-28 rounded-full"
                        />
                        <SkeletonBlock
                            dark
                            className="mb-3 h-11 w-3/4 max-w-3xl rounded-md"
                        />
                        <SkeletonBlock
                            dark
                            className="h-6 w-1/3 max-w-md rounded-md"
                        />
                    </div>
                </div>
                <div className="mt-4 space-y-2 sm:mt-6">
                    <SkeletonBlock className="h-6 w-64 rounded-md" />
                    <SkeletonBlock className="h-4 w-44 rounded-md" />
                    <SkeletonBlock className="h-4 w-80 max-w-full rounded-md" />
                </div>
            </section>
            <section className="mx-auto max-w-7xl space-y-8 px-4 pb-12 sm:px-6 lg:px-8">
                <SkeletonBlock className="h-16 w-full rounded-xl" />
                <ShowResultsSkeleton />
            </section>
        </main>
    );
}
