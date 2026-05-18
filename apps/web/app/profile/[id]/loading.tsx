import { SkeletonBlock } from "@/ui/components/loading/skeletons";

export default function Loading() {
    return (
        <div className="min-h-screen w-full bg-coconut-cream">
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
                <SkeletonBlock className="h-9 w-36 rounded-md" />
                <div className="hidden gap-4 sm:flex">
                    <SkeletonBlock className="h-8 w-20 rounded-md" />
                    <SkeletonBlock className="h-8 w-20 rounded-md" />
                </div>
            </div>

            <div className="max-w-7xl mx-auto">
                <div className="relative h-64 overflow-hidden bg-gradient-to-br from-cedar to-copper">
                    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-4">
                        <SkeletonBlock
                            dark
                            className="h-24 w-24 rounded-full"
                        />
                        <SkeletonBlock dark className="h-9 w-56 rounded-lg" />
                        <SkeletonBlock
                            dark
                            className="h-5 w-72 max-w-full rounded-lg"
                        />
                    </div>
                </div>

                <div className="border-b border-black/5 px-4 sm:px-6 lg:px-8">
                    <div className="flex gap-3 py-3">
                        <SkeletonBlock className="h-10 w-28 rounded-full" />
                        <SkeletonBlock className="h-10 w-36 rounded-full" />
                        <SkeletonBlock className="h-10 w-28 rounded-full" />
                    </div>
                </div>

                <div className="px-4 py-8 sm:px-6 lg:px-8">
                    <SkeletonBlock className="h-7 w-40 rounded-lg mb-6" />
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                        {Array.from({ length: 8 }).map((_, i) => (
                            <SkeletonBlock
                                key={i}
                                className="h-48 rounded-xl"
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
