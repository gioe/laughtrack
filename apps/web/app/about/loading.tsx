export default function Loading() {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            {/* About content section skeleton */}
            <div className="max-w-4xl mx-auto px-4 py-16">
                <div className="h-10 w-64 bg-gray-200 rounded-lg animate-pulse mb-6" />
                <div className="space-y-3">
                    <div className="h-4 w-full bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-4 w-5/6 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-4 w-4/6 bg-gray-200 rounded-lg animate-pulse" />
                </div>
            </div>

            {/* Stats section skeleton */}
            <div className="bg-gray-50 py-12">
                <div className="max-w-4xl mx-auto px-4">
                    <div className="grid grid-cols-3 gap-8 text-center">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="flex flex-col items-center gap-2">
                                <div className="h-10 w-24 bg-gray-200 rounded-lg animate-pulse" />
                                <div className="h-4 w-20 bg-gray-200 rounded-lg animate-pulse" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
