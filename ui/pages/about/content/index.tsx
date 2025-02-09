import { getCdnUrl } from "@/util/cdnUtil";
import React from "react";

const AboutUsSection = () => {
    const imageUrl = getCdnUrl("venue.png");

    return (
        <div className="w-full bg-cream-50">
            {/* Content Container */}
            <div className="max-w-7xl mx-auto px-6 py-12">
                {/* Header */}
                <h1 className="text-[32px] font-bold text-center mb-4 font-outfit">
                    About Us
                </h1>
                <p className="text-center text-gray-700 mb-8 font-dmSans text-[16px]">
                    Laughtrack is a space to find things that make you laugh,
                    and hopefully nothing else.
                </p>

                {/* Image Container - Fixed height with full width */}
                <div className="w-full h-[600px] mb-8 relative">
                    <img
                        src={imageUrl?.toString()}
                        alt={"Logo"}
                        className="w-full h-full object-cover rounded-lg"
                    />
                </div>

                {/* Text Content */}
                <div className="space-y-6 text-gray-700 text-left text-[18px] font-dmSans">
                    <p>
                        Laughtrack is a space to find things that make you
                        laugh, and hopefully nothing else.
                    </p>

                    <p>
                        Follow comedians you like. We'll let you know when
                        they're in your area. You wouldn't want to miss that one
                        time that one person on that one podcast was at a club
                        near you, would you?
                    </p>

                    <p>
                        Search for shows. We'll put them all in front of you and
                        let you know which we think you'll like. We'll even show
                        you places you probably didn't even know existed.
                    </p>

                    <p>
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
