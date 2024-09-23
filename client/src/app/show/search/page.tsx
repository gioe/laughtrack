import { getCurrentUser } from "@/actions/getCurrentUser";
import { getUpcomingShowResults } from "@/actions/getUpcomingShows";
import ClientOnly from "@/components/ClientOnly";
import Footer from "@/components/Footer";
import InfoCard from "@/components/InfoCard";
import MapComponent from "@/components/MapComponent";
import Header from "@/components/header/Header";
import { SearchResult, SearchResultResponse } from "@/interfaces/searchResult.interface";
import { UserInterface } from "@/interfaces/user.interface";
import moment from 'moment';

interface UpcomingShowProps {
    searchResultsResponse: SearchResultResponse;
    range: string;
    searchPlaceholder: string;
    location: string;
    user: UserInterface
}

const UpcomingShows: React.FC<UpcomingShowProps> = async ({
    searchResultsResponse,
    range,
    searchPlaceholder,
    location,
    user
}) => {


    return (
        <div>
            <Header
                currentUser={user}
                searchPlaceholder={searchPlaceholder}
            />
            <ClientOnly>
                <main className="flex">
                    <section className="flex-grow pt-14 px-6">
                        <p className="text-xs">{`${searchResultsResponse.total} shows ${range}`}</p>
                        
                        <h1 className="text-3xl font-semibold mt-2 mb-6">{`Shows in ${location}`}</h1>

                        <div className="hidden lg:inline-flex mb-5 space-x-3 text-gray-800 whitespace-nowrap">
                            <p className="search-filter">Sort Alphabetically</p>
                            <p className="search-filter">Sort by Popularity</p>
                            <p className="search-filter">Sort by Distance</p>
                        </div>
                        
                        <div className="flex flex-col">

                            {searchResultsResponse.results.map((comedian: SearchResult) => {
                                return (
                                    <InfoCard
                                        key={comedian.name}
                                        comedian={comedian} />
                                )
                            })}
                        </div>

                    </section>
                    <section className="hidden xl:inline-flex xl:min-w-[600px]">
                        <MapComponent searchResults={searchResultsResponse.coordinates} />
                    </section>

                </main>
            </ClientOnly>
            <Footer />
        </div>
    )
}

export default async function Page({ searchParams }: {
    searchParams: {
        location: string,
        startDate: string,
        endDate: string
    }
}) {
    const { location, startDate, endDate } = searchParams
    const formattedStartDate = moment(new Date(startDate)).format('ll')
    const formattedEndDate = moment(new Date(endDate)).format('ll')
    const range = `between ${formattedStartDate} - ${formattedEndDate}`
    const searchPlaceholder = `${location} | ${formattedStartDate} - ${formattedEndDate}`

    const searchResults = await getUpcomingShowResults(searchParams) as SearchResult[]
    const user = await getCurrentUser() as UserInterface;

    return (
        <UpcomingShows
            user={user}
            searchResults={searchResults}
            searchPlaceholder={searchPlaceholder}
            range={range}
            location={location}
        />
    )
}
