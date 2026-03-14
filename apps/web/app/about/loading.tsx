export default function Loading() {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            {/* About content section skeleton */}
            <div className="max-w-7xl mx-auto px-6 py-12">
                {/* Title */}
                <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse mx-auto mb-4" />
                {/* Subtitle */}
                <div className="h-4 w-72 bg-gray-200 rounded-lg animate-pulse mx-auto mb-8" />

                {/* Large image placeholder */}
                <div className="w-full h-[600px] bg-gray-200 rounded-lg animate-pulse mb-12" />

                {/* Text paragraphs */}
                <div className="space-y-8 max-w-3xl mx-auto">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="space-y-2">
                            <div className="h-4 w-full bg-gray-200 rounded-lg animate-pulse" />
                            <div className="h-4 w-5/6 bg-gray-200 rounded-lg animate-pulse" />
                            <div className="h-4 w-4/6 bg-gray-200 rounded-lg animate-pulse" />
                        </div>
                    ))}
                </div>
            </div>

            {/* Stats section skeleton */}
            <div className="w-full bg-coconut-cream py-16">
                <div className="max-w-7xl mx-auto px-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-12">
                        {[...Array(3)].map((_, i) => (
                            <div
                                key={i}
                                className="flex flex-col items-center gap-4"
                            >
                                {/* Icon */}
                                <div className="h-12 w-12 bg-gray-200 rounded-lg animate-pulse" />
                                {/* Count */}
                                <div className="h-10 w-24 bg-gray-200 rounded-lg animate-pulse" />
                                {/* Label */}
                                <div className="h-5 w-20 bg-gray-200 rounded-lg animate-pulse" />
                            </div>
                        ))}
                    </div>
                    {/* Description */}
                    <div className="max-w-3xl mx-auto space-y-2 text-center">
                        <div className="h-4 w-full bg-gray-200 rounded-lg animate-pulse" />
                        <div className="h-4 w-5/6 bg-gray-200 rounded-lg animate-pulse mx-auto" />
                    </div>
                </div>
            </div>
        </main>
    );
}
