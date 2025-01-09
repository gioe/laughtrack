"use client";

import React from "react";
import Link from "next/link";

export const Footer = () => {
    const currentYear = new Date().getFullYear();

    const handleContactClick = ({
        email = "admin@laughtrack-comedy.com",
        subject = "Hi!",
        body = "",
        cc = "",
        bcc = "",
    }) => {
        try {
            // Construct mailto URL with all parameters
            const mailtoUrl = new URL(`mailto:${email}`);

            // Add other email parameters
            const params = new URLSearchParams({
                subject: subject,
                body: body,
                ...(cc && { cc }),
                ...(bcc && { bcc }),
            });

            // Combine the URL and parameters
            const fullUrl = `${mailtoUrl}?${params.toString()}`;

            // Open default email client
            window.location.href = fullUrl;
        } catch (error) {
            console.error("Error opening email client:", error);
        }
    };

    return (
        <div className="flex flex-col bg-ivory">
            <div className="w-full draggable">
                <div className="container flex flex-col mx-auto p">
                    <div className="flex flex-col items-center w-full my-5">
                        <div className="flex flex-col items-center gap-6 mb-8">
                            <div className="flex flex-wrap items-center justify-center gap-5 lg:gap-12 gap-y-3 lg:flex-nowrap text-dark-grey-900">
                                <Link
                                    href="/about"
                                    className="text-copper font-fjalla"
                                >
                                    About
                                </Link>
                                <button
                                    onClick={() => {
                                        handleContactClick({});
                                    }}
                                    className="text-copper font-fjalla"
                                >
                                    Contact
                                </button>
                            </div>
                        </div>
                        <div className="flex items-center">
                            <p className="text-base font-fjalla leading-7 text-center text-copper">
                                {`© ${currentYear}. All Rights Reserved`}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Footer;
