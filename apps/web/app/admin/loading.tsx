import { Loader2 } from "lucide-react";

function SkeletonLine({ className }: { className: string }) {
    return (
        <div
            className={`animate-pulse rounded-md bg-soft-charcoal/15 ${className}`}
        />
    );
}

export default function AdminLoading() {
    return (
        <div role="status" aria-live="polite" className="space-y-6">
            <div className="flex items-center gap-3 rounded-md border border-copper/20 bg-white px-4 py-3 font-dmSans text-body font-semibold text-cedar shadow-sm">
                <Loader2 className="h-5 w-5 animate-spin text-copper-dark" />
                Loading admin section
            </div>

            <div className="space-y-3">
                <SkeletonLine className="h-5 w-28" />
                <SkeletonLine className="h-12 w-80 max-w-full" />
                <SkeletonLine className="h-5 w-[36rem] max-w-full" />
            </div>

            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                {Array.from({ length: 6 }, (_, index) => (
                    <div
                        key={index}
                        className="rounded-md border border-copper/20 bg-white p-4"
                    >
                        <div className="flex items-center gap-3">
                            <SkeletonLine className="h-10 w-10" />
                            <div className="min-w-0 flex-1 space-y-2">
                                <SkeletonLine className="h-3 w-20" />
                                <SkeletonLine className="h-7 w-14" />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="overflow-hidden rounded-md border border-copper/20 bg-white">
                <div className="border-b border-copper/15 bg-cedar px-4 py-3">
                    <SkeletonLine className="h-7 w-28 bg-coconut-cream/25" />
                </div>
                <div className="divide-y divide-copper/15">
                    {Array.from({ length: 4 }, (_, index) => (
                        <div
                            key={index}
                            className="grid gap-5 px-4 py-5 xl:grid-cols-[minmax(260px,0.8fr)_minmax(260px,0.8fr)_minmax(320px,1fr)]"
                        >
                            <div className="space-y-3">
                                <SkeletonLine className="h-7 w-64 max-w-full" />
                                <SkeletonLine className="h-5 w-72 max-w-full" />
                                <SkeletonLine className="h-4 w-full" />
                            </div>
                            <div className="space-y-3">
                                <SkeletonLine className="h-5 w-40" />
                                <SkeletonLine className="h-5 w-56" />
                                <SkeletonLine className="h-5 w-48" />
                            </div>
                            <div className="space-y-3">
                                <SkeletonLine className="h-5 w-60" />
                                <SkeletonLine className="h-5 w-52" />
                                <div className="flex flex-wrap gap-2">
                                    <SkeletonLine className="h-7 w-24" />
                                    <SkeletonLine className="h-7 w-28" />
                                    <SkeletonLine className="h-7 w-20" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
