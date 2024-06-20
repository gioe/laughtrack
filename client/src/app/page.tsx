import Home from '@/ui/pages/Home'
import { trending_data } from '@/data/trending'
import SearchForm from '@/components/SearchForm'

export default function Page() {
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
          {trending_data.map((item) => {
            return <div key={item.id} className="space-y-1 shrink-0 cursor-pointer">
              <img key={item.id} className="w-80 h-72 object-cover rounded-lg pb-2" alt='' src={item.src} />
              <p className="font-bold"> {item.title} </p>
              <p className="font-light text-sm"> {item.description} </p>

            </div>
          })}
        </div>
      </section>

    </main>
  )
}