import React from "react";
import { Theater, Users, Timer } from "lucide-react";

interface StatsSectionProps {
    clubCount: number;
    comedianCount: number;
    showCount: number;
}

const StatsSection: React.FC<StatsSectionProps> = ({
    clubCount,
    comedianCount,
    showCount,
}) => {
    return (
        <div className="w-full bg-coconut-cream py-16">
            <div className="max-w-7xl mx-auto px-4">
                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-8 mb-12">
                    {/* Clubs Stat */}
                    <div className="flex flex-col items-center">
                        <Theater className="w-12 h-12 text-copper mb-4" />
                        <h2 className="text-[40px] font-gilroy-bold font-bold mb-2">
                            {clubCount.toLocaleString()}
                        </h2>
                        <p className="text-gray-600 font-dmSans text-[19px]">
                            Clubs
                        </p>
                    </div>

                    {/* Comedians Stat */}
                    <div className="flex flex-col items-center">
                        <Users className="w-12 h-12 text-copper mb-4" />
                        <h2 className="text-[40px] font-gilroy-bold font-bold mb-2">
                            {comedianCount.toLocaleString()}
                        </h2>
                        <p className="text-gray-600 font-dmSans text-[19px]">
                            Comedians
                        </p>
                    </div>

                    {/* Shows Stat */}
                    <div className="flex flex-col items-center">
                        <Timer className="w-12 h-12 text-copper mb-4" />
                        <h2 className="text-[40px] font-gilroy-bold font-bold mb-2">
                            {showCount.toLocaleString()}
                        </h2>
                        <p className="text-gray-600 font-dmSans text-[19px]">
                            Shows
                        </p>
                    </div>
                </div>

                {/* Description Text */}
                <p className="text-center text-gray-700 max-w-3xl mx-auto font-dmSans">
                    Follow comedians you like. We'll let you know when they're
                    in your area. You wouldn't want to miss that one time that
                    one person on that one podcast was{" "}
                    <a
                        href="/show/search"
                        className="text-copper hover:underline"
                    >
                        at a club near you
                    </a>
                    , would you?
                </p>
            </div>
        </div>
    );
};

export default StatsSection;
