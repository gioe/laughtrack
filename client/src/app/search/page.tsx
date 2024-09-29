import { getCurrentUser } from "@/actions/getCurrentUser";
import { getUpcomingShowResults } from "@/actions/getUpcomingShows";
import SearchPageContents from "@/components/SearchPageContents";
import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import { UserInterface } from "@/interfaces/user.interface";
import moment from 'moment';
import Link from "next/link";

interface SearchPageProps {
    searchResults: SearchResultResponse;
    range: string;
    user: UserInterface
}

const SearchPage: React.FC<SearchPageProps> = async ({
    searchResults,
    range,
}) => {

    return (
        <div>
            <section className="flex-grow pt-14 px-6">
                <p className="text-xs text-silver-gray">{`${searchResults.shows.length} shows ${range}`}</p>

                <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`Shows in ${searchResults.city}`}</h1>

                <div className="hidden lg:inline-flex mb-5 space-x-3 text-silver-gray whitespace-nowrap">
                    <p className="search-filter">Sort by Popularity</p>
                    <p className="search-filter">Sort By Date</p>
                    <p className="search-filter">Sort By Surprise</p>
                </div>
                </section>
                <section>
                <SearchPageContents searchResults={searchResults} />
                </section>
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

    const searchResults = await getUpcomingShowResults(searchParams) as SearchResultResponse
    const user = await getCurrentUser() as UserInterface;

    return (
        <SearchPage
            user={user}
            searchResults={searchResults}
            range={range}
        />
    )
}
