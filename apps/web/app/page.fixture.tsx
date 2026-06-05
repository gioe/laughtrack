import ShowDiscoverySection from "@/ui/pages/home/shows";
import {
    CAROUSEL_TEST_IDS,
    FIXTURE_SHOWS_NEARBY,
    FIXTURE_SHOWS_TONIGHT,
    FIXTURE_SHOWS_TRENDING,
} from "@/lib/data/home/homeFixtures";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";

const FIXTURE_ZIP = "10801";

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
                    testId={CAROUSEL_TEST_IDS.showsTonight}
                />
            </section>
            <section className="w-full bg-white">
                <ShowDiscoverySection
                    title="Nearby Shows"
                    subtitle="Upcoming shows at clubs in your area"
                    shows={FIXTURE_SHOWS_NEARBY}
                    seeAllHref={`/show/search?zip=${FIXTURE_ZIP}&distance=${DEFAULT_HOME_RADIUS_MILES}`}
                    testId={CAROUSEL_TEST_IDS.nearbyShows}
                />
            </section>
            <section className="w-full bg-white">
                <ShowDiscoverySection
                    title="Trending This Week"
                    subtitle="The most popular shows happening in the next 7 days"
                    shows={FIXTURE_SHOWS_TRENDING}
                    seeAllHref="/show/search?sort=popularity_desc"
                    testId={CAROUSEL_TEST_IDS.trendingThisWeek}
                />
            </section>
        </main>
    );
}
