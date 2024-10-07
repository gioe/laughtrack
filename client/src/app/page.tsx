import { getTrendingComedians } from "@/actions/comedians/getTrendingComedians";
import { getCities } from "@/actions/cities/getCities";
import Link from "next/link";
import LargeComedianIcon from "@/components/custom/comedianIcons/LargeComedianIcon";
import SearchBar from "@/components/custom/filters/SearchBar";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { getLandingPageData } from "@/actions/landingPage/getLandingPageData";

interface LandingPageProps {
  trendingComedians: ComedianInterface[],
  cities: string[]
}


export default async function LandingPage() {

  const response = await getLandingPageData();

  return (
    <main>
      <section className="max-w-7xl mx-auto p-18">
        <h2 className="font-bold text-5xl text-white p-6">Find your next show</h2>
        <h3 className="text-white pt-1 p-5 text-xl">Search for shows from your favorite comedians. </h3>
      </section>

      <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
        <SearchBar cities={response.cities} />
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
          response.trendingComedians
            .sort((a, b) => (b.popularityScore ?? 0) - (a.popularityScore ?? 0))
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



