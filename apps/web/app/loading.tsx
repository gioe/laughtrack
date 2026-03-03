export default function Loading() {
    return (
        <div className="min-h-screen w-full bg-coconut-cream">
            {/* Hero Section Skeleton */}
            <div className="h-[60vh] w-full bg-gray-200 animate-pulse" />

            {/* Trending Comedians Skeleton */}
            <div className="max-w-7xl mx-auto px-4 py-8">
                <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse mb-8" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {[...Array(8)].map((_, i) => (
                        <div
                            key={i}
                            className="h-80 bg-gray-200 rounded-xl animate-pulse"
                        />
                    ))}
                </div>
            </div>

            {/* Trending Clubs Skeleton */}
            <div className="max-w-7xl mx-auto px-4 py-8">
                <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse mb-8" />
                <div className="flex gap-4 overflow-x-auto pb-4">
                    {[...Array(6)].map((_, i) => (
                        <div
                            key={i}
                            className="h-64 w-64 bg-gray-200 rounded-xl animate-pulse flex-shrink-0"
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
