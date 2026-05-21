import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Privacy Policy",
    alternates: { canonical: "/privacy" },
};

const PrivacyPage = async () => {
    return (
        <main
            id="main-content"
            className="min-h-screen w-full bg-coconut-cream"
        >
            <div className="max-w-3xl mx-auto px-6 py-12 font-dmSans text-base leading-relaxed text-white/85">
                <h1 className="text-3xl font-bold mb-2 text-white">Privacy Policy</h1>
                <p className="mb-10 text-xs text-white/55">
                    Last Updated: May 20, 2026
                </p>

                <div className="mb-10 space-y-4">
                    <p>
                        Laughtrack Digital, LLC (&ldquo;us&rdquo;,
                        &ldquo;we&rdquo;, or &ldquo;our&rdquo;) operates the
                        Laughtrack website at laugh-track.com and the Laughtrack
                        iOS mobile application (together, the
                        &ldquo;Service&rdquo;).
                    </p>
                    <p>
                        This page describes what data we collect when you use
                        the Service, how we use it, and the choices you have
                        about it. We try to keep the list short and to only
                        collect what we actually need to run the Service.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        1. Information We Collect
                    </h2>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        1.1 Account information (Google or Apple sign-in)
                    </h3>
                    <p>
                        You sign in with Google or Apple. When you do, the
                        identity provider returns the following information to
                        us, which we store so we can recognize your account on
                        return visits:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>Your email address</li>
                        <li>
                            Your name, if Google or Apple provides one (Apple
                            users can choose to hide their name and use a relay
                            email)
                        </li>
                        <li>
                            Your profile photo URL, if the identity provider
                            provides one
                        </li>
                        <li>
                            An internal user ID and the OAuth tokens issued by
                            Google or Apple. We use the tokens only to keep you
                            signed in and to refresh your session; we do not
                            use them to read other data from your Google or
                            Apple account.
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        1.2 Location and ZIP code
                    </h3>
                    <p>
                        Laughtrack uses ZIP codes (US 5-digit postal codes) to
                        show you comedy shows near you. You can provide a ZIP
                        code in two ways:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>
                            <strong>By typing it in.</strong> On the website,
                            your most recently chosen ZIP code is also cached
                            in your browser&rsquo;s local storage so the site
                            remembers it.
                        </li>
                        <li>
                            <strong>From your device location (iOS only).</strong>{" "}
                            If you tap &ldquo;Use my location&rdquo; in the iOS
                            app and grant location permission, the app reads
                            your device location, converts it to a 5-digit ZIP
                            code on-device, and discards the underlying
                            coordinates. Only the resulting ZIP code is sent to
                            our servers. We do not store or share your precise
                            location.
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        1.3 Your saved preferences
                    </h3>
                    <p>
                        While signed in, you can save preferences that we store
                        in your account so they follow you across devices:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>Comedians you favorite</li>
                        <li>Podcasts you favorite or claim ownership of</li>
                        <li>
                            Email and push notification preferences (whether
                            you want to be notified about shows)
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        1.4 Calendar (iOS only)
                    </h3>
                    <p>
                        If you tap &ldquo;Add to calendar&rdquo; on a show in
                        the iOS app, we ask iOS for write-only access to your
                        calendar so we can add that event. We do not read your
                        existing calendar entries, and we do not send any
                        calendar data to our servers.
                    </p>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        1.5 Usage and diagnostic data
                    </h3>
                    <p>
                        We collect a limited amount of standard server and
                        client diagnostic information so the Service stays up
                        and works correctly. This includes IP address, browser
                        or app version, device type, the pages you visit, and
                        timestamps. We do not use this data for advertising and
                        we do not sell it.
                    </p>
                    <p>
                        We also set the cookies necessary to keep you signed in
                        (a NextAuth session cookie) and to remember basic
                        preferences. We do not set advertising cookies.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        2. How We Use Your Data
                    </h2>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>To sign you in and keep you signed in</li>
                        <li>
                            To show you nearby and relevant comedy shows,
                            comedians, and podcasts
                        </li>
                        <li>To save the preferences you set</li>
                        <li>
                            To send you the notifications you have opted in to
                        </li>
                        <li>
                            To monitor the health of the Service and fix bugs
                            and crashes
                        </li>
                        <li>
                            To comply with legal obligations and protect the
                            Service from abuse
                        </li>
                    </ul>
                    <p>
                        We do not sell your personal information, and we do not
                        use it for third-party advertising.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        3. Service Providers We Share Data With
                    </h2>
                    <p>
                        We use the following third parties to run the Service.
                        They process data on our behalf, under their own
                        privacy policies, and only for the purposes listed:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>
                            <strong>Google and Apple</strong> &mdash; identity
                            providers for sign-in. They share your email, name,
                            and (for Google) profile photo URL with us when you
                            sign in.
                        </li>
                        <li>
                            <strong>Vercel</strong> &mdash; hosts the website
                            and collects standard request logs and aggregate
                            usage analytics (Vercel Analytics) so we can
                            monitor traffic and performance.
                        </li>
                        <li>
                            <strong>Neon</strong> &mdash; hosts our PostgreSQL
                            database, where your account, preferences, and ZIP
                            code are stored.
                        </li>
                        <li>
                            <strong>Sentry</strong> &mdash; receives error and
                            crash reports from the website so we can debug
                            issues. Reports may include your user ID and the
                            request that triggered the error.
                        </li>
                        <li>
                            <strong>Bunny CDN</strong> &mdash; serves images
                            (comedian photos, club photos, show artwork) from a
                            global edge network. Bunny sees standard delivery
                            metadata (IP, user agent) for image requests.
                        </li>
                    </ul>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        4. Data Transfers
                    </h2>
                    <p>
                        Your information may be processed and stored on servers
                        located outside your country or region, including in
                        the United States. By using the Service you consent to
                        that transfer.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        5. Disclosure for Legal Reasons
                    </h2>
                    <p>
                        We may disclose your information if we believe in good
                        faith that doing so is necessary to comply with a legal
                        obligation, protect the rights or property of
                        Laughtrack Digital, LLC or its users, investigate
                        possible wrongdoing in connection with the Service, or
                        protect against legal liability.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        6. Your Rights and Choices
                    </h2>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        6.1 Choices available to everyone
                    </h3>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>
                            You can revoke location or calendar permission for
                            the iOS app at any time in iOS Settings.
                        </li>
                        <li>
                            You can turn email and push notifications off in
                            your account settings.
                        </li>
                        <li>
                            You can request that we delete your account and the
                            personal data associated with it by emailing
                            admin@laugh-track.com.
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        6.2 California residents (CCPA/CPRA)
                    </h3>
                    <p>
                        If you are a California resident, you have the
                        following rights under the California Consumer Privacy
                        Act, as amended by the California Privacy Rights Act:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>
                            <strong>Right to know.</strong> You may request
                            confirmation of whether we process your personal
                            information and the categories of personal
                            information we have collected, the sources, the
                            purposes for which it is used, and the categories
                            of third parties with whom we share it. The
                            categories we collect are described in Section 1
                            of this policy.
                        </li>
                        <li>
                            <strong>Right to access.</strong> You may request
                            a copy of the specific pieces of personal
                            information we hold about you.
                        </li>
                        <li>
                            <strong>Right to delete.</strong> You may request
                            that we delete the personal information we have
                            collected from you, subject to legal exceptions
                            (for example, information we need to keep to
                            comply with a legal obligation).
                        </li>
                        <li>
                            <strong>Right to correct.</strong> You may request
                            that we correct inaccurate personal information we
                            hold about you.
                        </li>
                        <li>
                            <strong>Right to opt out of sale or sharing.</strong>{" "}
                            We do not sell your personal information and we
                            do not share it for cross-context behavioral
                            advertising, so there is nothing to opt out of.
                            If that ever changes, we will update this policy
                            and provide a clear opt-out before the change
                            takes effect.
                        </li>
                        <li>
                            <strong>Right to non-discrimination.</strong> We
                            will not deny you the Service, charge you a
                            different price, or provide you a different level
                            of quality for exercising any of these rights.
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        6.3 EU, EEA, and UK residents (GDPR/UK GDPR)
                    </h3>
                    <p>
                        If you are in the European Union, European Economic
                        Area, or United Kingdom, you have the following
                        rights under the GDPR and UK GDPR:
                    </p>
                    <ul className="list-disc pl-6 space-y-1">
                        <li>
                            <strong>Right of access.</strong> You may obtain
                            confirmation of whether we process your personal
                            data and a copy of that data.
                        </li>
                        <li>
                            <strong>Right to rectification.</strong> You may
                            ask us to correct inaccurate or incomplete
                            personal data.
                        </li>
                        <li>
                            <strong>Right to erasure.</strong> You may ask us
                            to delete your personal data, subject to legal
                            exceptions.
                        </li>
                        <li>
                            <strong>Right to data portability.</strong> You
                            may receive your personal data in a structured,
                            commonly used, machine-readable format and ask us
                            to transmit it to another controller where
                            technically feasible.
                        </li>
                        <li>
                            <strong>Right to restriction of processing.</strong>{" "}
                            You may ask us to limit how we use your personal
                            data in certain circumstances.
                        </li>
                        <li>
                            <strong>Right to object.</strong> You may object
                            to our processing of your personal data,
                            including for direct marketing.
                        </li>
                        <li>
                            <strong>Right to withdraw consent.</strong> Where
                            we rely on consent to process your data, you may
                            withdraw that consent at any time without
                            affecting the lawfulness of processing carried
                            out before withdrawal.
                        </li>
                        <li>
                            <strong>Right to lodge a complaint.</strong> You
                            have the right to lodge a complaint with your
                            local data protection supervisory authority.
                        </li>
                    </ul>

                    <h3 className="text-xl font-semibold mt-6 mb-2">
                        6.4 How to exercise these rights
                    </h3>
                    <p>
                        To exercise any of the rights described above, email{" "}
                        <a
                            href="mailto:admin@laugh-track.com"
                            className="underline text-white"
                        >
                            admin@laugh-track.com
                        </a>{" "}
                        from the email address associated with your
                        Laughtrack account, or include enough information for
                        us to verify your identity. We will respond within
                        <strong> 30 days</strong> of receiving a verifiable
                        request. If we need more time (up to an additional 60
                        days under the CCPA, or two months under the GDPR),
                        we will let you know within the initial 30-day
                        window. You may also designate an authorized agent to
                        make a request on your behalf, subject to
                        verification.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        7. Security
                    </h2>
                    <p>
                        We use commercially reasonable measures to protect your
                        information, but no method of transmission over the
                        Internet or method of electronic storage is 100%
                        secure, and we cannot guarantee absolute security.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        8. Children&rsquo;s Privacy
                    </h2>
                    <p>
                        The Service is not directed to anyone under the age of
                        18. We do not knowingly collect personal information
                        from anyone under the age of 18. If you believe a
                        minor has provided us with personal information,
                        please email admin@laugh-track.com and we will delete
                        it.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        9. Changes To This Privacy Policy
                    </h2>
                    <p>
                        We may update this Privacy Policy from time to time.
                        When we do, we will update the &ldquo;Last
                        Updated&rdquo; date at the top of this page. Material
                        changes will be highlighted in the Service before they
                        take effect.
                    </p>
                </div>

                <div className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold mt-8 mb-2">
                        10. Contact Us
                    </h2>
                    <p>
                        Questions about this Privacy Policy? Email{" "}
                        <a
                            href="mailto:admin@laugh-track.com"
                            className="underline text-white"
                        >
                            admin@laugh-track.com
                        </a>
                        .
                    </p>
                </div>
            </div>
        </main>
    );
};

export default PrivacyPage;
