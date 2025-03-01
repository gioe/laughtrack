"use client";

import { openEmailClient } from "@/ui/components/button/contact";

const FooterComponent = () => {
    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault();
        openEmailClient({
            to: "contact@laugh-track.com",
            subject: "Inquiry",
            body: "",
        });
    };
    return (
        <footer className="py-16 border-t border-gray-200 bg-coconut-cream">
            <div className="max-w-7xl mx-auto px-8">
                {/* Main footer content */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 mb-12">
                    {/* Brand and description */}
                    <div className="lg:col-span-8">
                        <h2 className="text-[30px] font-bold text-[#2D1810] mb-4 font-gilroy-bold">
                            Laughtrack
                        </h2>
                        <p className="text-[17px] text-gray-600 max-w-2xl font-dmSans">
                            Laughtrack is the easiest way to explore and enjoy
                            comedy. Really the only way if we're being honest.
                        </p>
                    </div>
                </div>

                {/* Bottom bar */}
                <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-gray-200">
                    {/* Copyright */}
                    <div className="text-gray-600 mb-4 md:mb-0 text-[17px] font-dmSans">
                        Copyright © 2025 Laughtrack Digital, LLC
                    </div>

                    {/* Links and socials */}
                    <div className="flex items-center space-x-8">
                        {/* Footer links */}
                        <nav className="flex space-x-6">
                            <a
                                href="/about"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                About
                            </a>
                            <a
                                href="#"
                                onClick={handleClick}
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Contact
                            </a>
                            <a
                                href="/privacy"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Privacy
                            </a>
                            <a
                                href="/terms"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Terms and Conditions
                            </a>
                            {/* <a
                                href="/support"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Support
                            </a> */}
                        </nav>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default FooterComponent;
