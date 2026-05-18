import { SkeletonBlock } from "@/ui/components/loading/skeletons";

export default function Loading() {
    return (
        <main
            id="main-content"
            className="min-h-screen w-full bg-coconut-cream"
        >
            <div className="max-w-7xl mx-auto px-6 py-12">
                <div className="text-center mb-8">
                    <SkeletonBlock className="h-12 w-48 rounded-lg mx-auto mb-4" />
                    <SkeletonBlock className="h-6 w-80 max-w-full rounded-lg mx-auto" />
                </div>

                <SkeletonBlock className="w-full h-[600px] rounded-lg mb-12 shadow-xl" />

                <div className="space-y-8 max-w-3xl mx-auto">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="space-y-2">
                            <SkeletonBlock className="h-6 w-full rounded-lg" />
                            <SkeletonBlock className="h-6 w-5/6 rounded-lg" />
                            <SkeletonBlock className="h-6 w-4/6 rounded-lg" />
                        </div>
                    ))}
                </div>
            </div>

            <div className="w-full bg-coconut-cream py-16">
                <div className="max-w-7xl mx-auto px-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-12">
                        {Array.from({ length: 3 }).map((_, i) => (
                            <div
                                key={i}
                                className="flex flex-col items-center gap-4"
                            >
                                <SkeletonBlock className="h-12 w-12 rounded-lg" />
                                <SkeletonBlock className="h-10 w-24 rounded-lg" />
                                <SkeletonBlock className="h-5 w-20 rounded-lg" />
                            </div>
                        ))}
                    </div>
                    <div className="max-w-3xl mx-auto space-y-2 text-center">
                        <SkeletonBlock className="h-5 w-full rounded-lg" />
                        <SkeletonBlock className="h-5 w-5/6 rounded-lg mx-auto" />
                    </div>
                </div>
            </div>
        </main>
    );
}
