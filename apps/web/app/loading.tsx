export default function Loading() {
    return (
        <div className="min-h-screen w-full bg-coconut-cream">
            {/* Hero Section Skeleton */}
            <div className="h-[60vh] w-full bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:400%_100%] animate-shimmer" />

            {/* Trending Comedians Skeleton */}
            <div className="max-w-7xl mx-auto px-4 py-8">
                <div className="h-8 w-48 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:400%_100%] animate-shimmer rounded-lg mb-8" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {[...Array(8)].map((_, i) => (
                        <div
                            key={i}
                            className="h-80 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:400%_100%] animate-shimmer rounded-xl"
                        />
                    ))}
                </div>
            </div>

            {/* Trending Clubs Skeleton */}
            <div className="max-w-7xl mx-auto px-4 py-8">
                <div className="h-8 w-48 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:400%_100%] animate-shimmer rounded-lg mb-8" />
                <div className="flex gap-4 overflow-x-auto pb-4">
                    {[...Array(6)].map((_, i) => (
                        <div
                            key={i}
                            className="h-64 w-64 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:400%_100%] animate-shimmer rounded-xl flex-shrink-0"
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
