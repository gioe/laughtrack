export default function Loading() {
    return (
        <main
            id="main-content"
            className="min-h-screen w-full bg-coconut-cream"
        >
            <div className="max-w-7xl mx-auto px-6 py-12">
                {/* Title */}
                <div className="h-9 w-36 bg-gray-200 rounded-lg animate-pulse mx-auto mb-4" />

                {/* Large image placeholder */}
                <div className="w-full h-[600px] bg-gray-200 rounded-lg animate-pulse mb-8" />

                {/* Text paragraphs */}
                <div className="space-y-6 max-w-3xl mx-auto">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="space-y-2">
                            <div className="h-4 w-full bg-gray-200 rounded-lg animate-pulse" />
                            <div className="h-4 w-5/6 bg-gray-200 rounded-lg animate-pulse" />
                            <div className="h-4 w-4/6 bg-gray-200 rounded-lg animate-pulse" />
                        </div>
                    ))}
                </div>
            </div>
        </main>
    );
}
