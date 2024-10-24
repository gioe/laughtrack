import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults, HomeSearchParams, HomeSearchResultResponse } from "@/actions/search/getSearchResults";
import FilterPageContainer, { FilterOption } from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' },
  { name: 'Price: Low to High', value: 'low_to_high' },
  { name: 'Price: High to Low', value: 'high_to_low' }
]

export default async function CityDetailPage(
  props: {
    searchParams: Promise<HomeSearchParams>;
  }
) {
  const searchParams = await props.searchParams;

  const searchResults = await getSearchResults(searchParams) as HomeSearchResultResponse;
  const title = buildTitle(searchParams, searchResults)
  const filters = buildFilters(searchParams, searchResults)

  return (

    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        itemCount={searchResults.totalShows}
        title={title}
        searchPlaceholder={'Search for comics'}
        query={searchParams.query}
        filterOptions={filters}
        defaultSort={sortOptions[0].value}
        sortOptions={sortOptions}
        child={<SearchResultsTable searchResults={searchResults} />} />
    </main>
  )
}

const buildFilters = (params: any, results: any) => {

  const clubFilter = {
    id: 'clubs',
    name: 'Clubs',
    options: results.clubs.map((clubName: string) => {
      return {
        value: clubName.toLowerCase(),
        label: clubName,
        selected: params.clubs?.includes(clubName.toLowerCase())
      } as FilterOption;
    })
  }

  const priceFilter = {
    id: 'prices',
    name: 'Price Range',
    options: [
      {
        value: 'free',
        label: "Free",
        selected: false
      },
      {
        value: '1-20',
        label: "$1 to $20",
        selected: false
      },
      {
        value: '21-50',
        label: "$21 to $50",
        selected: false
      },
      {
        value: '51-100',
        label: "$51 to $100",
        selected: false
      },
      {
        value: '100+',
        label: "$100+",
        selected: false
      }
    ]
  }

  const showType = {
    id: 'type',
    name: 'Show Type',
    options: [
      {
        value: 'open-mic',
        label: "Open Mic",
        selected: false
      },
      {
        value: 'standup',
        label: "Standup",
        selected: false
      },
      {
        value: 'podcast',
        label: "Live Podcast",
        selected: false
      },
      {
        value: 'sketch',
        label: "Sketch",
        selected: false
      }
    ]
  }


  return [clubFilter, priceFilter, showType];
}

const buildTitle = (params: any, results: any): string => {
  const formattedStartDate = params?.startDate ? moment(new Date(params.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = params?.endDate ? moment(new Date(params.endDate)).format('ll') : moment(new Date()).format('ll')
  const range = `between ${formattedStartDate} - ${formattedEndDate}`
  return `${results.totalShows} shows in ${results.entity.name} ${range}`
}
