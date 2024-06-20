'use client';

import Home from '@/ui/pages/Home'
import { trending_data } from '@/data/trending'
import SearchForm from '@/components/SearchForm'
import { useEffect, useState } from 'react'
import { Comedian } from '@/util/types';

export default function Page() {

  const [allComedians, setAllComedians] = useState<Comedian[]>([])
  const [trendingComedians, setTrendingComedians] = useState<Comedian[]>([])

  useEffect(() => {
    fetch("http://localhost:8080/api/comedians/all").then(
      response => response.json()
    ).then(
      data => {
        const fetchedComedians = data.comedians as Comedian[]
        const trendingComedians = fetchedComedians.splice(0,5)
        const sortedComedians = fetchedComedians.sort((a, b) => a.name.localeCompare(b.name))
        console.log(trendingComedians)
        setAllComedians(sortedComedians)
        setTrendingComedians(trendingComedians)
      }
    )
  }, [setAllComedians, setTrendingComedians]);

  return (
    <main className="bg-[#1B262C]">
      <section className='max-w-7xl mx-auto p-6'>
        <h2 className="font-bold text-5xl text-white"> Find the funny </h2>
        <h3 className="text-white py-5 text-xl"> Search for your favorite comedians </h3>
      </section>

      <section className='m-4 mt-0 -mb-14 px-2 lg:px-4'>
        <SearchForm />
      </section>

      <section className='mx-auto max-w-7xl mt-10 bg-white rounded-t-lg'>
        <div className='pt-5'>
          <h3 className='text-xl font-bold'> Trending Comedians </h3>
          <p className='font-light'> Most high performing comedians from around the country.</p>
        </div>

        <div className="flex space-x-4 py-5 overflow-x-scroll">
          {trendingComedians.map((item) => {
            return <div key={item.name} className="space-y-1 shrink-0 cursor-pointer">
              <img key={item.name} className="w-80 h-72 object-cover rounded-lg pb-2" alt='' src={item.name} />
              <p className="font-bold"> {item.name} </p>
              <p className="font-light text-sm"> {`${item.showCount} shows`} </p>
            </div>
          })}
        </div>
      </section>

    </main>
  )
}