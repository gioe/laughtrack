import { getTrendingComedians } from "@/actions/getTrendingComedians";
import { getCities } from "@/actions/getCities";
import Link from "next/link";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import LargeComedianIcon from "@/components/custom/comedianIcons/LargeComedianIcon";
import SearchBar from "@/components/custom/search/SearchBar";

interface LandingPageProps {
  trendingComedians: ComedianInterface[],
  cities: string[]
}

const LandingPage: React.FC<LandingPageProps> = async ({
  trendingComedians,
  cities
}) => {
  return (
    <main>
      <section className="max-w-7xl mx-auto p-18">
        <h2 className="font-bold text-5xl text-white p-6">Find your next show</h2>
        <h3 className="text-white pt-1 p-5 text-xl">Search for shows from your favorite comedians. </h3>
      </section>

      <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
        <SearchBar cities={cities} />
      </section>

      <section className="
      flex flex-col mx-auto max-w-7xl mt-10 
      p-6 rounded-lg mb-4 bg-white">
        <div className="flex flex-row-reverse items-end">
          <Link
          className="items-center"
            href='comedian/all'>
            <div className="text-blue-400 text-sm font-medium underline">See all</div>
          </Link>
        </div>

        <div className="flex space-x-3 overflow-scroll
         scrollbar-hide p-3 -ml-3">
          {
          trendingComedians
            .sort((a, b) => b.popularityScore - a.popularityScore)
            .map((comedian: ComedianInterface) => {
              return (
                <LargeComedianIcon key={comedian.name} comedian={comedian} />
              )
            })
            }
        </div>
      </section>
    </main>
  );
}


export default async function Page({ params }: {
  params: {
    location: string,
    startDate: string,
    endDate: string
  }
}) {

  const trendingComedians = await getTrendingComedians() as ComedianInterface[]
  const cities = await getCities() as string[]

  return (
    <LandingPage cities={cities} trendingComedians={trendingComedians} />
  )
}




