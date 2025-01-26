import React from "react";

const SupportSection = () => {
    const imageUrl = new URL(
        `venue.png`,
        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
    );

    return (
        <div className="w-full bg-cream-50">
            {/* Content Container */}
            <div className="max-w-7xl mx-auto px-6 py-12">
                {/* Header */}
                <h1 className="text-[32px] font-bold text-center mb-4 font-outfit">
                    Support
                </h1>

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
                        We built Laughtrack because we saw a problem that needed
                        solving. It's not the biggest problem in the world, but
                        it's a real one. We're not trying to disrupt industries
                        or harvest attention. We simply wanted to build
                        something helpful and sustainable. No venture capital,
                        no big tech backing - just regular people using our
                        skills to create something useful.
                    </p>

                    <p>
                        While the site is free, there are real costs to keeping
                        it running smoothly. If you've found value in using this
                        product and want to contribute to its continued
                        development, consider making a one-time or recurring
                        contribution. Your support directly enables ongoing
                        improvements and helps ensure the site's longevity.
                    </p>

                    <p>
                        We're an accessible team - if you have suggestions for
                        the product, email us at admin@laughtrack-comedy.com.
                        More interest means more resources we can dedicate to
                        building features that benefit everyone or, I guess,
                        anyone.
                    </p>

                    <p>Thank you for the support.</p>
                </div>
            </div>
        </div>
    );
};

export default SupportSection;
