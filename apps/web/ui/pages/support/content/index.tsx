import React from "react";
import { getCdnUrl } from "@/util/cdnUtil";

const SupportSection = () => {
    const imageUrl = getCdnUrl("venue.png");

    return (
        <div className="w-full bg-coconut-cream">
            <div className="max-w-7xl mx-auto px-6 py-12">
                <div className="text-center mb-8">
                    <h1 className="text-h1 font-bold mb-4 font-chivo">
                        Support
                    </h1>
                    <p className="text-muted-foreground font-dmSans text-body max-w-3xl mx-auto">
                        Need help with Laughtrack? Email us and we'll send a
                        first human response within 2 business days.
                    </p>
                </div>

                <div className="w-full h-[600px] mb-8 relative">
                    <img
                        src={imageUrl?.toString()}
                        alt="Comedy venue"
                        className="w-full h-full object-cover rounded-lg"
                    />
                </div>

                <div className="space-y-10 text-muted-foreground text-left font-dmSans max-w-3xl mx-auto">
                    <section className="space-y-4">
                        <h2 className="font-chivo text-3xl font-bold text-foreground">
                            Report a bug or ask for help
                        </h2>
                        <p className="text-lead">
                            Send support requests, bug reports, broken ticket
                            links, missing venue details, and product
                            suggestions to{" "}
                            <a
                                href="mailto:contact@laugh-track.com"
                                className="font-semibold text-copper underline underline-offset-4 hover:text-cedar"
                            >
                                contact@laugh-track.com
                            </a>
                            .
                        </p>
                        <p className="text-lead">
                            We check the inbox on business days and aim to send
                            a first human response within 2 business days of
                            receiving your message. That first response may be a
                            quick acknowledgement, a clarifying question, or the
                            next step we're taking.
                        </p>
                    </section>

                    <section className="space-y-4 border-t border-copper/25 pt-8">
                        <h2 className="font-chivo text-3xl font-bold text-foreground">
                            Keeping Laughtrack useful
                        </h2>
                        <p className="text-lead">
                            We built Laughtrack because finding live comedy
                            should be simpler. The site is free to use, and
                            there are real costs to keeping the data fresh and
                            the product running smoothly.
                        </p>
                        <p className="text-lead">
                            More interest gives us more room to improve the
                            product, keep fixing rough edges, and build features
                            that help people find shows worth leaving the house
                            for.
                        </p>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default SupportSection;
