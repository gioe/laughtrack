"use server";

import { Instagram, Linkedin } from "lucide-react";

const FooterComponent = () => {
    return (
        <footer className="py-16 border-t border-gray-200">
            <div className="max-w-7xl mx-auto px-8">
                {/* Main footer content */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 mb-12">
                    {/* Brand and description */}
                    <div className="lg:col-span-8">
                        <h2 className="text-[30px] font-bold text-[#2D1810] mb-4 font-chivo">
                            Laughtrack
                        </h2>
                        <p className="text-[17px] text-gray-600 max-w-2xl font-dmSans">
                            Laughtrack is the easiest way to explore and enjoy
                            comedy. Whether you're searching for a show tonight,
                            following your favorite comedians, or discovering
                            new grassroots venues, we've got you covered.
                        </p>
                    </div>
                </div>

                {/* Bottom bar */}
                <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-gray-200">
                    {/* Copyright */}
                    <div className="text-gray-600 mb-4 md:mb-0 text-[17px]">
                        Copyright © 2025 Laughtrack
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
                                href="/contact"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Contact
                            </a>
                            <a
                                href="/support"
                                className="text-gray-600 hover:text-copper transition-colors text-[17px] font-dmSans font-semibold"
                            >
                                Support
                            </a>
                        </nav>

                        {/* Social icons */}
                        {/* <div className="flex space-x-4">
                            <a
                                href="https://instagram.com/laughtrack"
                                className="text-gray-600 hover:text-[#CD7F32] transition-colors"
                                aria-label="Instagram"
                            >
                                <Instagram size={20} />
                            </a>
                            <a
                                href="https://linkedin.com/company/laughtrack"
                                className="text-gray-600 hover:text-[#CD7F32] transition-colors"
                                aria-label="LinkedIn"
                            >
                                <Linkedin size={20} />
                            </a>
                        </div> */}
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default FooterComponent;
