import { SkeletonBlock } from "@/ui/components/loading/skeletons";

export default function Loading() {
    return (
        <main
            id="main-content"
            className="min-h-screen w-full bg-coconut-cream"
        >
            <div className="max-w-7xl mx-auto px-6 py-12">
                <SkeletonBlock className="h-12 w-36 rounded-lg mx-auto mb-4" />

                <SkeletonBlock className="w-full h-[600px] rounded-lg mb-8" />

                <div className="space-y-6 text-left">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="space-y-2">
                            <SkeletonBlock className="h-6 w-full rounded-lg" />
                            <SkeletonBlock className="h-6 w-5/6 rounded-lg" />
                            <SkeletonBlock className="h-6 w-4/6 rounded-lg" />
                        </div>
                    ))}
                </div>
            </div>
        </main>
    );
}
