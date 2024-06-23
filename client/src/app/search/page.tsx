'use client';

import { Show } from "@/util/types";
import Link from "next/link";
import { useEffect, useState } from "react";

type Props = {
    searchParams: SearchParams
}

export type SearchParams = {
    url: URL;
    name: string;
    from: string;
    to: string;
}


function SearchPage({searchParams}: Props) {
    const [comedianName, setComedianName] = useState<string>('')
    const [shows, setShows] = useState<Show[]>([])

    useEffect(() => {
      fetch(`http://localhost:8080/api/comedians/?name=${searchParams.name}&from=${searchParams.from}&to=${searchParams.to}`).then(
        response => response.json()
      ).then(
        data => {
            console.log(data.comedian.name)
            console.log(data.comedian.shows)
            setComedianName(data.comedian.name)
            setShows(data.comedian.shows)
        }
      )
    }, [setComedianName, setShows]);

    return (
      <section> 
        <div className="mx-auto max-w-7xl p-6 lg:px-8">
            <h1 className="text-4xl font-bold pb-3"> Results </h1>

            <h2 className="pb-3">
                Show dates:
                <span className="italic ml-2">
                    {searchParams.from} to {searchParams.to}
                </span>
            </h2>

            <hr className="mb-5" />

            <h3 className="font-semibold text-xl" >

            </h3>

            <div className="space-y-2 mt-5">
                {shows.length === 0 ? <></> : shows.map((item, i) => {
                    return <div
                    key={i}
                    className="flex space-y-2 justify-between space-x-4 p-5 border rounded-lg"
                    >
                        <img 
                        src={""}
                        alt="image of the comedian"
                        className="h-44 w-44 rounded=lg"
                        />

                        <div className="flex flex-1 space-x-5 justify-between">
                            <div>
                                <Link 
                                href={item.ticketLink}
                                className="font-bold text-blue-500 hover:text-blue-600 hover:underline"
                                >
                                    {item.name}
                                </Link>
                                <p className="text-xs">{item.clubName}</p>
                            </div>
                        </div>
                    </div>
                })}
            </div>
        </div>
      </section>
    ) 
}

export default SearchPage;