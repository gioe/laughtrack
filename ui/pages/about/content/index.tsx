import React from "react";

const AboutUsSection = () => {
    const imageUrl = new URL(
        `logo.png`,
        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
    );

    return (
        <div className="w-full bg-cream-50">
            {/* Content Container */}
            <div className="max-w-4xl mx-auto px-6 py-12">
                {/* Header */}
                <h1 className="text-3xl font-bold text-center mb-4">
                    About Us
                </h1>
                <p className="text-center text-gray-700 mb-8">
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
                <div className="space-y-6 text-gray-700">
                    <p>
                        Laughtrack is a space to find things that make you
                        laugh, and hopefully nothing else. Follow comedians you
                        like. We'll let you know when they're in your area. You
                        wouldn't want to miss that one time that one person on
                        that one podcast was at a club near you, would you?
                    </p>

                    <p>
                        Search for shows of your liking. We'll put them all in
                        front of you and let you know which we think you'll
                        like. We'll even show you places and shows you probably
                        didn't even know existed.
                    </p>

                    <p>
                        We just want to clean up the comedy space a little bit.
                        Enjoying yourself shouldn't be so hard!
                    </p>

                    <p>
                        Donec laoreet mi in finibus. Integer consequat ultricies
                        ante, non venenatis justo fermentum ut. Etiam porttitor,
                        arcu a imperdiet pulvinar, sem felis facilisis dui,
                        vitae mollis ipsum ex et diam. Quisque eu hendrerit leo,
                        vitae iaculis erat. Proin euismod felis risus, sit amet
                        vestibulum massa aliquam vel.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AboutUsSection;
