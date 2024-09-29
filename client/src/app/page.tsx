import { getTrendingClubs } from "@/actions/getTrendingClubs";
import { getTrendingComedians } from "@/actions/getTrendingComedians";
import { getCities } from "@/actions/getCities";
import MediumComedianCard from "@/components/MediumComedianCard";
import Search from "@/components/Search";
import Link from "next/link";
import { ComedianInterface } from "@/interfaces/comedian.interface";

interface LandingPageProps {
  trendingComedians: ComedianInterface[],
  cities: string[]
}

const LandingPage: React.FC<LandingPageProps> = async ({
  trendingComedians,
  cities
}) => {
  return (
    <main className="bg-shark">

      <section className="max-w-7xl mx-auto p-18">
        <h2 className="font-bold text-5xl text-white pt-6">Find your next show</h2>
        <h3 className="text-white py-5 text-xl">Search for shows from your favorite comedians. Follow them to know when they're coming to you.</h3>
      </section>

      <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
        <Search cities={cities} />
      </section>

      <section className="mx-auto max-w-7xl mt-10 p-6 bg-white rounded-lg mb-4">
        <div className="">
          <Link
            href='comedian/all'>
            <div>See all</div>
          </Link>
        </div>

        <div className="flex space-x-3 overflow-scroll scrollbar-hide p-3 -ml-3">
          {
          trendingComedians
            .sort((a, b) => b.popularityScore - a.popularityScore)
            .map((comedian: ComedianInterface) => {
              return (
                <MediumComedianCard key={comedian.name} comedian={comedian} />
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




