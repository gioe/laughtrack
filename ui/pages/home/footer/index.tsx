"use client";

import { openEmailClient } from "@/ui/components/button/contact";

const FooterComponent = () => {
    const handleClick = (e) => {
        e.preventDefault();
        openEmailClient({
            to: "contact@laugh-track.com",
            subject: "Inquiry",
            body: "",
        });
    };

    return (
        <footer className="py-8 sm:py-12 md:py-16 border-t border-gray-200 bg-coconut-cream">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-6 sm:gap-8 mb-8 sm:mb-12">
                    <div className="lg:col-span-8">
                        <h2 className="text-2xl sm:text-[30px] font-bold text-[#2D1810] mb-2 sm:mb-4 font-gilroy-bold">
                            Laughtrack
                        </h2>
                        <p className="text-base sm:text-[17px] text-gray-600 max-w-2xl font-dmSans">
                            Laughtrack is the easiest way to explore and enjoy
                            comedy. Really the only way.
                        </p>
                    </div>
                </div>

                <div className="flex flex-col md:flex-row justify-between items-center pt-6 sm:pt-8 border-t border-gray-200">
                    <div className="text-gray-600 mb-4 md:mb-0 text-sm sm:text-base md:text-[17px] font-dmSans">
                        Copyright © 2025 Laughtrack Digital, LLC
                    </div>

                    <div className="flex flex-wrap justify-center md:justify-end items-center gap-4 sm:gap-6 md:gap-8">
                        <nav className="flex flex-wrap justify-center gap-4 sm:gap-6">
                            <a
                                href="/about"
                                className="text-gray-600 hover:text-copper transition-colors text-sm sm:text-base md:text-[17px] font-dmSans font-semibold"
                            >
                                About
                            </a>
                            <a
                                href="#"
                                onClick={handleClick}
                                className="text-gray-600 hover:text-copper transition-colors text-sm sm:text-base md:text-[17px] font-dmSans font-semibold"
                            >
                                Contact
                            </a>
                            <a
                                href="/privacy"
                                className="text-gray-600 hover:text-copper transition-colors text-sm sm:text-base md:text-[17px] font-dmSans font-semibold"
                            >
                                Privacy
                            </a>
                            <a
                                href="/terms"
                                className="text-gray-600 hover:text-copper transition-colors text-sm sm:text-base md:text-[17px] font-dmSans font-semibold"
                            >
                                Terms
                            </a>
                        </nav>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default FooterComponent;
