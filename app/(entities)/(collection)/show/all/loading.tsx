export default function Loading() {
    return (
        <div className="max-w-full mx-auto px-4 py-8 bg-ivory">
            <div className="max-w-7xl">
                <div className="space-y-2 mb-8">
                    <div className="h-8 w-64 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-4 w-24 bg-gray-200 rounded-lg animate-pulse" />
                </div>

                {/* Filter Bar */}
                <div className="flex flex-wrap gap-4 items-center mb-8">
                    <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-10 w-48 bg-gray-200 rounded-lg animate-pulse" />
                    <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
                </div>

                {/* Show Cards */}
                <div className="space-y-6">
                    {[1, 2, 3].map((item) => (
                        <div
                            key={item}
                            className="flex items-center gap-6 p-6 bg-white/50 rounded-xl"
                        >
                            {/* Venue Image */}
                            <div className="h-16 w-16 bg-gray-200 rounded-lg animate-pulse flex-shrink-0" />

                            {/* Show Details */}
                            <div className="flex-grow space-y-3">
                                <div className="h-6 w-48 bg-gray-200 rounded-lg animate-pulse" />
                                <div className="h-4 w-96 bg-gray-200 rounded-lg animate-pulse" />
                                <div className="h-4 w-72 bg-gray-200 rounded-lg animate-pulse" />
                            </div>

                            {/* Get Tickets Button */}
                            <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse flex-shrink-0" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
