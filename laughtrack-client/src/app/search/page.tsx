'use client';

import { getShowSearchResults } from "@/actions/getShowSearchResults";
import Footer from "@/components/Footer";
import InfoCard from "@/components/InfoCard";
import MapComponent from "@/components/MapComponent";
import Navbar from "@/components/navbar/Navbar";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { format } from "date-fns";
import { useSearchParams } from "next/navigation";
import { Suspense } from 'react'

const Search = async () => {

    const searchParams = useSearchParams()
    const location = searchParams.get("location")
    const startDate = searchParams.get("startDate") ?? ""
    const endDate = searchParams.get("endDate") ?? ""

    const formattedStartDate = format(new Date(startDate), 'dd MMMM yy')
    const formattedEndDate = format(new Date(endDate), 'dd MMMM yy')
    const range = `between ${formattedStartDate} - ${formattedEndDate}`
    const searchPlaceholder = `${location} | ${formattedStartDate} - ${formattedEndDate}`

    const searchResults = await getShowSearchResults({location, startDate, endDate}) as ComedianInterface[]
    console.log(searchResults)

    return (
        <div>
            <Navbar searchPlaceholder={searchPlaceholder} />
            <main className="flex">
                <section className="flex-grow pt-14 px-6"> 
                    <p className="text-xs">{`400 shows ${range}`}</p>
                    <h1 className="text-3xl font-semibold mt-2 mb-6">{`Performances in ${location}`}</h1>

                    <div className="hidden lg:inline-flex mb-5 space-x-3 text-gray-800 whitespace-nowrap">
                        <p className="button">Sort Alphabetically</p>
                        <p className="button">Sort by Popularity</p>
                        <p className="button">Sort by Distance</p>
                    </div>
                    <div className="flex flex-col">

                    {searchResults.map((comedian: ComedianInterface) => {
                        return (
                            <InfoCard 
                            key={comedian.name}
                            comedian={comedian} />
                        )
                    })}
                    </div>

                </section>
                <section className="hidden xl:inline-flexn xl:min-w-[600px]">
                    <MapComponent searchResults={searchResults} />
                </section>

            </main>
            <Footer />
        </div>
    )
}

const Searchbar = async () => {
    return (
        <Suspense>
        <Search />
       </Suspense>
    ) 
 }

 export default Searchbar;