import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import { getCdnUrl } from "@/util/cdnUtil";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import ShowSearchForm from "@/ui/components/params/search/pages/home";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import Image from "next/image";
import Link from "next/link";
import { formatShowDate } from "@/util/dateUtil";

interface HeroComponentProps {
    profile?: UserProfileInterface | null;
    city?: string | null;
    state?: string | null;
    heroShows?: ShowDTO[];
    hasLocalShows?: boolean;
}

function buildHeadline(city: string | null, state: string | null): string {
    if (!city) return "Get out and laugh";
    const locale = state ? `${city}, ${state}` : city;
    return `What's funny near ${locale}?`;
}

function buildSubtitle(city: string | null, hasLocalShows: boolean): string {
    if (city && hasLocalShows) {
        return `The next shows within ${DEFAULT_HOME_RADIUS_MILES} miles`;
    }
    if (city) {
        return "Start with popular shows from across LaughTrack, then tune the search below.";
    }
    return "Find live comedy shows, clubs, and comedians near you.";
}

function getShowTitle(show: ShowDTO): string {
    return show.name || show.clubName || "Comedy show";
}

function getLineupLabel(show: ShowDTO): string | null {
    const names = show.lineup?.map((comedian) => comedian.name).filter(Boolean);
    if (!names?.length) return null;
    const displayNames = names.slice(0, 2).join(", ");
    const extraCount = names.length - 2;
    return extraCount > 0
        ? `${displayNames} +${extraCount} more`
        : displayNames;
}

function HeroShowTile({ show }: { show: ShowDTO }) {
    const title = getShowTitle(show);
    const lineupLabel = getLineupLabel(show);

    return (
        <Link
            href={`/show/${show.id}`}
            aria-label={`View details for ${title}`}
            data-testid="hero-show-tile"
            className="group flex min-h-[96px] overflow-hidden rounded-lg border border-white/15 bg-white/12 text-left shadow-lg shadow-black/15 backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-white/18 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
        >
            <div className="relative h-auto w-16 flex-none overflow-hidden bg-cedar-dark/40 sm:w-24">
                <Image
                    src={show.imageUrl}
                    alt=""
                    fill
                    className="object-cover transition duration-300 group-hover:scale-105"
                    sizes="96px"
                    aria-hidden="true"
                />
            </div>
            <div className="flex min-w-0 flex-col justify-center gap-1 px-2 py-2 sm:px-3">
                <p className="line-clamp-2 font-gilroy-bold text-xs font-bold leading-tight text-white sm:text-sm">
                    {title}
                </p>
                {show.clubName && show.name && (
                    <p className="truncate font-dmSans text-xs text-white/75">
                        {show.clubName}
                    </p>
                )}
                <p className="line-clamp-1 font-dmSans text-xs text-white/80">
                    {formatShowDate(show.date.toString(), show.timezone)}
                </p>
                {lineupLabel && (
                    <p className="line-clamp-1 font-dmSans text-xs text-white/65">
                        w/ {lineupLabel}
                    </p>
                )}
            </div>
        </Link>
    );
}

const HeroComponent = ({
    profile,
    city = null,
    state = null,
    heroShows = [],
    hasLocalShows = false,
}: HeroComponentProps) => {
    const headline = buildHeadline(city, state);
    const subtitle = buildSubtitle(city, hasLocalShows);

    return (
        <section className="relative w-full min-h-[380px] sm:min-h-[600px] md:min-h-[700px] lg:min-h-[776px] overflow-hidden">
            <BackgroundImage
                imageUrl={getCdnUrl(`laughtrack-hero.png`)}
                alt={"Header background image"}
            />
            <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" />
            <ContentWrapper>
                <Navbar currentUser={profile} />
                <div className="flex flex-col items-center justify-center text-center w-full px-4 sm:px-6 md:px-6 lg:px-6 relative pt-8 sm:pt-12 md:pt-12 lg:pt-14 pb-12 sm:pb-16 md:pb-16 lg:pb-20">
                    <div className="animate-fadeIn w-full max-w-6xl">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-6xl xl:text-7xl font-bold mb-4 sm:mb-6 md:mb-6 lg:mb-6 font-chivo text-white drop-shadow-lg">
                            {headline}
                        </h1>
                        <p className="text-lg sm:text-xl md:text-2xl lg:text-2xl text-gray-100 mb-8 sm:mb-10 md:mb-10 lg:mb-10 max-w-3xl mx-auto font-chivo animate-slideUp opacity-90">
                            {subtitle}
                        </p>
                        {heroShows.length > 0 && (
                            <div
                                data-testid="home-hero-show-grid"
                                className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 mb-8 sm:mb-10 md:mb-10 lg:mb-10"
                            >
                                {heroShows.map((show) => (
                                    <HeroShowTile key={show.id} show={show} />
                                ))}
                            </div>
                        )}
                        <div className="transform transition-all duration-300 hover:scale-[1.01]">
                            <ShowSearchForm />
                        </div>
                    </div>
                </div>
            </ContentWrapper>
        </section>
    );
};

export default HeroComponent;
