export default function Loading() {
    return (
        <div className="min-h-screen w-full bg-coconut-cream">
            {/* Header Section */}
            <div className="space-y-2 mb-8">
                <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse" />
                <div className="h-4 w-24 bg-gray-200 rounded-lg animate-pulse" />
            </div>

            {/* Filter Bar */}
            <div className="flex flex-wrap gap-4 items-center mb-8">
                <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
                <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse" />
                <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse" />
                <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
            </div>

            {/* Club Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {[1, 2, 3, 4, 5, 6, 8].map((item) => (
                    <div
                        key={item}
                        className="flex flex-col items-center text-center"
                    >
                        {/* Club Image */}
                        <div className="h-64 w-full bg-gray-200 rounded-xl animate-pulse mb-4" />

                        {/* Club Name */}
                        <div className="h-6 w-48 bg-gray-200 rounded-lg animate-pulse mb-2" />

                        {/* Club Address */}
                        <div className="h-4 w-56 bg-gray-200 rounded-lg animate-pulse" />
                    </div>
                ))}
            </div>
        </div>
    );
}
