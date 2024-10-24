'use server';

import { ComedianInterface } from "@/interfaces/comedian.interface";
import LargeComedianInfoCard from "@/components/custom/tables/cards/LargeComedianInfoCard";
import LandingPageSearchBar from "@/components/custom/filters/LandingPageSearchBar";
import { cookies } from "next/headers";
import { LandingPageResponseInterface } from "@/interfaces/landingPageResponse.interface";

export default async function LandingPage() {


  const getCities = async () => {
    const res = await fetch('http://localhost:3000/api/cities', {
      headers: { Cookie: cookies().toString() },
    })
    console.log(res)
    return res.json()
  }


  // const getTrendingComedians = async () => {
  //   const res = await fetch('http://localhost:3000/api/trending')
  //   console.log(res)
  //   return res.json()
  // }

  // const getLandingPageData  = async () => {
  //   return Promise.all([getCities(), getTrendingComedians()]).then((responses: any[]) => {
  //     return {
  //       cities: responses[0],
  //       trendingComedians: responses[1],
  //     } as LandingPageResponseInterface
  //   })
  // }

  const response = await getCities()

  return (
    <main>
      <section className="max-w-7xl mx-auto p-18">
        <h2 className="font-bold text-5xl text-white p-5">Laughtrack</h2>
        <h3 className="text-white pt-1 p-5 text-xl">Find your next show</h3>
      </section>

      <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
        <LandingPageSearchBar cities={response.cities} />
      </section>

      <section className="
      flex flex-col mx-auto max-w-7xl mt-10 
      p-6 rounded-lg mb-4 bg-white">
        <div className="flex space-x-3 overflow-scroll
         scrollbar-hide p-3 -ml-3">
          {
            // response.trendingComedians
            //   .sort((a, b) => (b.socialData?.popularityScore ?? 0) - (a.socialData?.popularityScore ?? 0))
            //   .map((comedian: ComedianInterface) => {
            //     return (
            //       <LargeComedianInfoCard key={comedian.name} comedian={comedian} />
            //     )
            //   })
          }
        </div>
      </section>
    </main>
  );
}
