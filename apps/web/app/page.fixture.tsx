import ShowDiscoverySection from "@/ui/pages/home/shows";
import {
    FIXTURE_SHOWS_TONIGHT,
    FIXTURE_SHOWS_TRENDING,
} from "@/lib/data/home/homeFixtures";

export default function FixtureHomePage() {
    return (
        <main id="main-content" className="min-h-screen w-full">
            <h1 className="sr-only">LaughTrack</h1>
            <section className="w-full bg-white">
                <ShowDiscoverySection
                    title="Shows Tonight"
                    subtitle="Live comedy happening right now, near you"
                    shows={FIXTURE_SHOWS_TONIGHT}
                    seeAllHref="/show/search"
                />
            </section>
            <section className="w-full bg-white">
                <ShowDiscoverySection
                    title="Trending This Week"
                    subtitle="The most popular shows happening in the next 7 days"
                    shows={FIXTURE_SHOWS_TRENDING}
                    seeAllHref="/show/search?sort=popularity_desc"
                />
            </section>
        </main>
    );
}
