import Navbar from "@/ui/components/navbar";
import BackgroundImage from "@/ui/components/background";
import ContentWrapper from "@/ui/components/wrapper";
import { getCdnUrl } from "@/util/cdnUtil";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import ShowSearchForm from "@/ui/components/params/search/pages/home";
import CompactShowCard from "@/ui/components/cards/show/compact";
import { ShowDTO } from "@/objects/class/show/show.interface";

interface HeroComponentProps {
    profile?: UserProfileInterface | null;
    city?: string | null;
    state?: string | null;
    heroShows?: ShowDTO[];
}

function buildHeadline(city: string | null, state: string | null): string {
    if (!city) return "Get out and laugh";
    const locale = state ? `${city}, ${state}` : city;
    return `What's funny near ${locale}?`;
}

const HeroComponent = ({
    profile,
    city = null,
    state = null,
    heroShows = [],
}: HeroComponentProps) => {
    const hasLocalShows = heroShows.length > 0;
    const headline = buildHeadline(city, state);
    const subtitle =
        city && hasLocalShows
            ? "The next shows within 5 miles"
            : city
              ? "No local shows found — try expanding your search below."
              : "Find live comedy shows, clubs, and comedians near you.";

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
                        {hasLocalShows && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-4 mb-8 sm:mb-10 md:mb-10 lg:mb-10 text-left">
                                {heroShows.map((show) => (
                                    <CompactShowCard
                                        key={show.id}
                                        show={show}
                                    />
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
