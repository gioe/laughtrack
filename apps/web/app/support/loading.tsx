export default function Loading() {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <div className="max-w-2xl mx-auto px-4 py-16">
                {/* Title */}
                <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse mb-4" />
                {/* Subtitle */}
                <div className="h-4 w-72 bg-gray-200 rounded-lg animate-pulse mb-10" />

                {/* Form fields */}
                <div className="space-y-6">
                    {[...Array(3)].map((_, i) => (
                        <div key={i}>
                            <div className="h-4 w-24 bg-gray-200 rounded-lg animate-pulse mb-2" />
                            <div className="h-10 w-full bg-gray-200 rounded-lg animate-pulse" />
                        </div>
                    ))}
                    {/* Message textarea */}
                    <div>
                        <div className="h-4 w-24 bg-gray-200 rounded-lg animate-pulse mb-2" />
                        <div className="h-32 w-full bg-gray-200 rounded-lg animate-pulse" />
                    </div>
                    {/* Submit button */}
                    <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
                </div>
            </div>
        </main>
    );
}
