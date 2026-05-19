// Collection-route layout convention
// --------------------------------------------------------------------------
// Every page under (entities)/(collection) renders a SearchDetailHeader hero,
// a FilterBar control strip, and then a result list. The result-list shape is
// intentionally NOT uniform across entities:
//
//   - /show/search renders a vertical list of full-width rows. A show row
//     carries a date stack, title, venue, datetime, price, "Get Tickets" CTA,
//     and a horizontal lineup-avatar strip — six pieces of metadata plus two
//     interactive elements. None of that compresses cleanly into a card, and
//     the CTA is the product's primary conversion action.
//
//   - /comedian/search, /club/search, /podcast/search render a 4-column grid.
//     These entities are "discoverable" — face-first / cover-art-first
//     recognition matters more than transactional metadata, and grid density
//     wins for browse-with-intent traffic.
//
// In short: transactional entity → list with CTA. Discoverable entity → grid.
// If a future entity falls in the latter bucket, follow the grid pattern. If
// you find yourself adding a CTA-bearing entity, the list pattern is correct.
// The iOS app uses LaughTrackEntityRow uniformly because mobile screen
// constraints force every tab into a single shape; the web isn't constrained
// the same way, so the per-entity choice is deliberate.

import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import { Suspense } from "react";
import ErrorBoundary from "@/ui/components/errorBoundary";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Navbar currentUser={session?.profile} />
            <ErrorBoundary>
                <Suspense>
                    <main
                        id="main-content"
                        className="flex-1 w-full bg-coconut-cream px-4 sm:px-6 md:px-8"
                    >
                        {children}
                    </main>
                </Suspense>
            </ErrorBoundary>
            <FooterComponent />
        </StyleContextProvider>
    );
}
