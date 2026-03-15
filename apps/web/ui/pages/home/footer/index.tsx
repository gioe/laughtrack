"use client";

import React, { MouseEvent } from "react";
import { openEmailClient } from "@/ui/components/button/contact";
import XIcon from "@/ui/components/icons/XIcon";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import { siteConfig } from "@/ui/config/siteConfig";

const SOCIAL_LINKS: {
    label: string;
    href: string;
    Icon: React.ComponentType<{ size?: string; className?: string }>;
}[] = [
    {
        label: "Twitter / X",
        href: `https://x.com/${siteConfig.social.twitter}`,
        Icon: XIcon,
    },
    {
        label: "Instagram",
        href: `https://instagram.com/${siteConfig.social.instagram}`,
        Icon: InstagramIcon,
    },
    {
        label: "TikTok",
        href: `https://tiktok.com/@${siteConfig.social.tiktok}`,
        Icon: TikTokIcon,
    },
];

const FooterComponent = () => {
    const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();
        openEmailClient({
            to: "contact@laugh-track.com",
            subject: "Inquiry",
            body: "",
        });
    };

    return (
        <footer className="bg-gradient-to-b from-coconut-cream to-[#F5E6D3]">
            {/* Copper accent strip */}
            <div className="h-1 bg-gradient-to-r from-transparent via-copper to-transparent opacity-60" />

            <div className="py-16 sm:py-20 max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8 sm:gap-12 mb-12 sm:mb-16">
                    <div className="lg:col-span-8">
                        <h2
                            className="text-3xl sm:text-4xl font-bold text-cedar mb-4 sm:mb-6 font-gilroy-bold
                            transform transition-all duration-300 hover:scale-[1.02]"
                        >
                            Laughtrack
                        </h2>
                        <p className="text-lg sm:text-xl text-gray-600 max-w-2xl font-dmSans leading-relaxed">
                            Laughtrack is the easiest way to explore and enjoy
                            comedy. Really the only way.
                        </p>
                    </div>

                    <div className="lg:col-span-4 flex flex-col justify-center md:items-end">
                        <p className="text-sm text-gray-500 font-dmSans mb-3 md:text-right">
                            Follow us
                        </p>
                        <div className="flex gap-3 md:justify-end">
                            {SOCIAL_LINKS.map(({ label, href, Icon }) => (
                                <a
                                    key={label}
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={label}
                                    className="transition-transform duration-200 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-copper rounded-full"
                                >
                                    <Icon size="w-9 h-9" />
                                </a>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex flex-col md:flex-row justify-between items-center pt-8 sm:pt-10 border-t border-gray-200">
                    <div className="text-gray-600 mb-6 md:mb-0 text-base sm:text-lg font-dmSans">
                        Copyright © 2025 Laughtrack Digital, LLC
                    </div>

                    <nav className="flex flex-wrap justify-center gap-6 sm:gap-8">
                        <a
                            href="/about"
                            className="text-gray-600 hover:text-copper transition-all duration-200
                            text-base sm:text-lg font-dmSans font-semibold hover:-translate-y-[1px]"
                        >
                            About
                        </a>
                        <a
                            href="#"
                            onClick={handleClick}
                            className="text-gray-600 hover:text-copper transition-all duration-200
                            text-base sm:text-lg font-dmSans font-semibold hover:-translate-y-[1px]"
                        >
                            Contact
                        </a>
                        <a
                            href="/privacy"
                            className="text-gray-600 hover:text-copper transition-all duration-200
                            text-base sm:text-lg font-dmSans font-semibold hover:-translate-y-[1px]"
                        >
                            Privacy
                        </a>
                        <a
                            href="/terms"
                            className="text-gray-600 hover:text-copper transition-all duration-200
                            text-base sm:text-lg font-dmSans font-semibold hover:-translate-y-[1px]"
                        >
                            Terms
                        </a>
                    </nav>
                </div>
            </div>
        </footer>
    );
};

export default FooterComponent;
