import Link from "next/link";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import { formatTicketString } from "@/util/ticket/ticketUtil";
import { Ticket } from "@/objects/class/ticket/Ticket";
import { TicketDTO } from "@/objects/class/ticket/ticket.interface";

interface ShowTicketCtaProps {
    show: ShowDetailDTO;
}

// Picks the best external URL to send the user to: a live ticket row, else the
// scraped show page. Falls back to null only when the row is a past show with
// no URLs at all, in which case we render nothing.
function pickTicketUrl(show: ShowDetailDTO): string | null {
    const tickets = show.tickets ?? [];
    const live = tickets.find((t: TicketDTO) => !t.soldOut && t.purchaseUrl);
    if (live?.purchaseUrl) return live.purchaseUrl;
    const firstUrl = tickets.find((t: TicketDTO) => t.purchaseUrl)?.purchaseUrl;
    if (firstUrl) return firstUrl;
    return show.showPageUrl || null;
}

const ShowTicketCta: React.FC<ShowTicketCtaProps> = ({ show }) => {
    const url = pickTicketUrl(show);
    const tickets = (show.tickets ?? []).map((t) => new Ticket(t));
    const liveTickets = tickets.filter((t) => !t.soldOut);
    const priceLabel = formatTicketString(liveTickets);

    if (show.isPast) {
        return (
            <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-8 mb-10">
                <div className="inline-flex items-center gap-3 px-5 py-3 rounded-xl bg-stone-100 border border-stone-200">
                    <span className="text-base text-gray-600 font-dmSans">
                        This show has ended.
                    </span>
                </div>
            </section>
        );
    }

    if (show.soldOut || liveTickets.length === 0) {
        return (
            <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-8 mb-10">
                <div className="inline-flex items-center gap-3 px-5 py-3 rounded-xl bg-red-50 border border-red-200">
                    <span className="text-base font-semibold text-red-700 font-dmSans">
                        Sold Out
                    </span>
                </div>
            </section>
        );
    }

    if (!url) return null;

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-8 mb-10">
            <Link
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-copper text-white font-gilroy-bold font-bold text-[16px] shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                Get Tickets
                {priceLabel && (
                    <span className="text-white/90 font-dmSans font-normal">
                        · {priceLabel}
                    </span>
                )}
            </Link>
            <p className="mt-2 text-xs text-gray-500 font-dmSans">
                Opens the venue&apos;s ticketing page in a new tab.
            </p>
        </section>
    );
};

export default ShowTicketCta;
