export default function Loading() {
    return (
        <div className="min-h-screen w-full bg-coconut-cream">
            {/* Navbar skeleton */}
            <div className="h-16 w-full bg-gray-200 animate-pulse" />

            {/* User header skeleton */}
            <div className="max-w-4xl mx-auto px-4 py-12">
                <div className="flex flex-col items-center gap-4">
                    {/* Avatar */}
                    <div className="h-24 w-24 rounded-full bg-gray-200 animate-pulse" />
                    {/* Name */}
                    <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse" />
                    {/* Bio */}
                    <div className="h-4 w-64 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-4 w-48 bg-gray-200 rounded-lg animate-pulse" />
                </div>

                {/* Favorites section */}
                <div className="mt-12">
                    <div className="h-6 w-40 bg-gray-200 rounded-lg animate-pulse mb-6" />
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                        {[...Array(8)].map((_, i) => (
                            <div
                                key={i}
                                className="h-48 bg-gray-200 rounded-xl animate-pulse"
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Footer skeleton */}
            <div className="h-32 w-full bg-gray-200 animate-pulse mt-8" />
        </div>
    );
}
