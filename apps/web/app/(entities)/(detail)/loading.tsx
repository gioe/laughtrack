import React from "react";

export default function Loading() {
    return (
        <div className="w-full mx-auto p-6 animate-pulse bg-coconut-cream">
            {/* Header */}
            <div className="max-w-7xl mx-auto p-6 animate-pulse">
                <div className="flex items-center gap-4 mb-8">
                    <div className="w-16 h-16 rounded-full bg-gray-200" />
                    <div className="flex-1">
                        <div className="h-6 bg-gray-200 rounded w-64 mb-2" />
                        <div className="h-4 bg-gray-200 rounded w-48" />
                    </div>
                    <div className="flex gap-4">
                        <div className="h-10 w-20 bg-gray-200 rounded" />
                        <div className="h-10 w-20 bg-gray-200 rounded" />
                    </div>
                </div>

                {/* Main Images */}
                <div className="grid grid-cols-3 gap-4 mb-8">
                    <div className="col-span-2 h-96 bg-gray-200 rounded" />
                    <div className="space-y-4">
                        <div className="h-44 bg-gray-200 rounded" />
                        <div className="h-44 bg-gray-200 rounded" />
                    </div>
                </div>

                {/* Upcoming Shows Section */}
                <div className="mb-8">
                    <div className="h-8 bg-gray-200 rounded w-48 mb-4" />
                    <div className="h-4 bg-gray-200 rounded w-32 mb-6" />

                    {/* Show Cards */}
                    {[1, 2].map((i) => (
                        <div
                            key={i}
                            className="mb-8 p-6 bg-gray-100 rounded-lg"
                        >
                            <div className="flex items-center gap-4 mb-6">
                                <div className="w-16 h-16 rounded-full bg-gray-200" />
                                <div className="flex-1">
                                    <div className="h-6 bg-gray-200 rounded w-48 mb-2" />
                                    <div className="h-4 bg-gray-200 rounded w-64" />
                                </div>
                                <div className="h-10 w-32 bg-gray-200 rounded" />
                            </div>

                            {/* Performer Images */}
                            <div className="flex gap-4">
                                {[1, 2, 3, 4, 5].map((j) => (
                                    <div key={j} className="flex-1">
                                        <div className="aspect-square bg-gray-200 rounded mb-2" />
                                        <div className="h-4 bg-gray-200 rounded w-24" />
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* About Section */}
                <div>
                    <div className="h-8 bg-gray-200 rounded w-32 mb-4" />
                    <div className="space-y-3">
                        <div className="h-4 bg-gray-200 rounded w-full" />
                        <div className="h-4 bg-gray-200 rounded w-5/6" />
                        <div className="h-4 bg-gray-200 rounded w-4/5" />
                    </div>
                </div>
            </div>
        </div>
    );
}
