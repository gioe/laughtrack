import { getCdnUrl } from "@/util/cdnUtil";
import React from "react";

const AboutUsSection = () => {
    const imageUrl = getCdnUrl("venue.png");

    return (
        <div className="w-full bg-coconut-cream">
            <div className="max-w-7xl mx-auto px-6 py-12">
                {/* Header with fade-in and slide-up animation */}
                <div className="text-center mb-8 animate-fadeIn">
                    <h1 className="text-h1 font-bold mb-4 font-chivo bg-gradient-to-r from-copper to-cedar bg-clip-text text-transparent transform transition-transform duration-300 hover:scale-105">
                        About Us
                    </h1>
                    <p className="text-gray-700 font-dmSans text-body animate-slideUp">
                        Laughtrack is a space to find things that make you
                        laugh, and hopefully nothing else.
                    </p>
                </div>

                {/* Image Container with hover effects */}
                <div className="w-full h-[600px] mb-12 relative overflow-hidden rounded-lg shadow-xl group">
                    <img
                        src={imageUrl?.toString()}
                        alt="Comedy Venue"
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent transition-opacity duration-300 group-hover:opacity-50" />
                </div>

                {/* Text Content with staggered animations */}
                <div className="space-y-8 text-gray-700 text-left text-lead font-dmSans max-w-3xl mx-auto">
                    <p className="animate-fadeIn [animation-delay:100ms]">
                        Laughtrack is a space to find things that make you
                        laugh, and hopefully nothing else.
                    </p>

                    <p className="animate-fadeIn [animation-delay:200ms]">
                        Follow comedians you like. We'll let you know when
                        they're in your area. You wouldn't want to miss that one
                        time that one person on that one podcast was at a club
                        near you, would you?
                    </p>

                    <p className="animate-fadeIn [animation-delay:300ms]">
                        Search for shows. We'll put them all in front of you and
                        let you know which we think you'll like. We'll even show
                        you places you probably didn't even know existed.
                    </p>

                    <p className="animate-fadeIn [animation-delay:400ms]">
                        We just want to clean up the comedy space a little bit
                        and make it easier to find good times. Enjoying yourself
                        shouldn't be so hard.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AboutUsSection;
