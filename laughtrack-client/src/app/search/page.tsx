'use client';

import { getShowSearchResults } from "@/actions/getShowSearchResults";
import Footer from "@/components/Footer";
import Navbar from "@/components/navbar/Navbar";
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

    const results = await getShowSearchResults({location, startDate, endDate})

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