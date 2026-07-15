import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Delete Your Laughtrack Account",
    description:
        "Instructions for deleting a Laughtrack account and its associated data.",
    alternates: { canonical: "/account-deletion" },
};

const AccountDeletionPage = () => {
    return (
        <main
            id="main-content"
            className="min-h-screen w-full bg-coconut-cream"
        >
            <div className="max-w-3xl mx-auto px-6 py-12 font-dmSans text-base leading-relaxed text-white/85">
                <h1 className="text-3xl font-bold mb-4 text-white">
                    Delete Your Laughtrack Account
                </h1>
                <p className="mb-8">
                    Laughtrack Digital, LLC lets you permanently delete your
                    Laughtrack account and the personal data associated with it.
                    You can delete it directly in the iOS or Android app, or
                    request deletion by email without installing the app.
                </p>

                <section className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold text-white">
                        Delete your account in the app
                    </h2>
                    <ol className="list-decimal pl-6 space-y-2">
                        <li>Sign in to Laughtrack.</li>
                        <li>Open the Profile tab.</li>
                        <li>Tap &ldquo;Delete account.&rdquo;</li>
                        <li>Confirm permanent deletion.</li>
                    </ol>
                    <p>
                        The app sends the deletion request immediately. This
                        action cannot be undone.
                    </p>
                </section>

                <section className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold text-white">
                        Request deletion without the app
                    </h2>
                    <p>
                        Email us from the address associated with your
                        Laughtrack account. Use the subject &ldquo;Laughtrack
                        account deletion request&rdquo; and ask us to delete
                        your account and associated data.
                    </p>
                    <a
                        href="mailto:admin@laugh-track.com?subject=Laughtrack%20account%20deletion%20request"
                        className="inline-flex rounded-full bg-white px-5 py-3 font-semibold text-black hover:bg-white/90"
                    >
                        Request account deletion
                    </a>
                    <p>
                        We may ask for information needed to verify that you own
                        the account. We will process a verified request within
                        30 days.
                    </p>
                </section>

                <section className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold text-white">
                        Data that is deleted
                    </h2>
                    <p>
                        Account deletion removes the following data from
                        Laughtrack&rsquo;s active systems:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                        <li>
                            Account identity, including your name, email
                            address, profile-photo URL, and internal user ID
                        </li>
                        <li>
                            Your saved ZIP code, distance, onboarding state, and
                            notification preferences
                        </li>
                        <li>Favorite comedians, comedy clubs, and podcasts</li>
                        <li>
                            Device push-notification tokens and active mobile
                            refresh tokens
                        </li>
                        <li>Notification history linked to your account</li>
                    </ul>
                </section>

                <section className="mb-10 space-y-4">
                    <h2 className="text-2xl font-semibold text-white">
                        Limited data that may be retained
                    </h2>
                    <p>
                        Laughtrack does not impose an additional fixed retention
                        period on account data after deletion. Residual copies
                        may remain temporarily in encrypted backups until the
                        normal backup-rotation cycle overwrites them. Backup
                        copies are reserved for disaster recovery and are not
                        used for ordinary product operations.
                    </p>
                    <p>
                        We may retain limited security, fraud-prevention,
                        transaction, or legal records only where necessary to
                        comply with law, resolve disputes, prevent abuse, or
                        enforce our agreements. Aggregated or de-identified data
                        that can no longer reasonably identify you may also be
                        retained.
                    </p>
                </section>

                <section className="space-y-4">
                    <h2 className="text-2xl font-semibold text-white">
                        Questions
                    </h2>
                    <p>
                        Contact{" "}
                        <a
                            href="mailto:admin@laugh-track.com"
                            className="underline text-white"
                        >
                            admin@laugh-track.com
                        </a>
                        . You can also read our{" "}
                        <a href="/privacy" className="underline text-white">
                            Privacy Policy
                        </a>
                        .
                    </p>
                </section>
            </div>
        </main>
    );
};

export default AccountDeletionPage;
