import { getCurrentUser } from "@/actions/getCurrentUser";
import { getTrendingClubs } from "@/actions/getTrendingClubs";
import { getTrendingComedians } from "@/actions/getTrendingComedians";
import Banner from "@/components/Banner";
import ClientOnly from "@/components/ClientOnly";
import Header from "@/components/header/Header";
import MediumCard from "@/components/MediumCard";
import SmallCard from "@/components/SmallCard";
import { TrendingClub } from "@/interfaces/trendingClub.interface";
import { TrendingComedian } from "@/interfaces/trendingComedian";
import { UserInterface } from "@/interfaces/user.interface";

interface LandingPageProps {
  trendingComedians: TrendingComedian[],
  trendingClubs: TrendingClub[],
  user: UserInterface
}

const LandingPage: React.FC<LandingPageProps> = async ({
  trendingComedians,
  trendingClubs,
  user
}) => {

  return (
    <div>
      <ClientOnly>
        <Header
          currentUser={user} />
        <Banner />
        <main className="max-w-7xl mx-auto px-8 sm:px-16">
          <section className="pt-6">
            <h2 className="text-4xl font-semibold pb-5">Popular Clubs</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
              {trendingClubs
                .sort((a, b) => b.count - a.count)
                .map((item: any) => {
                  return (
                    <SmallCard key={item.name} name={item.name} url={item.url} filePath={item.image_name} />
                  )
                })}
            </div>
          </section>

          <section>
            <h2 className="text-4xl font-semibold py-8">Trending Comedians</h2>

            <div className="flex space-x-3 overflow-scroll scrollbar-hide p-3 -ml-3">
              {trendingComedians
                .sort((a, b) => b.count - a.count)
                .map((item: any) => {
                  return (
                    <MediumCard key={item.name} name={item.name} instagram={item.instagram} count={item.count} />
                  )
                })}
            </div>
          </section>

        </main>
      </ClientOnly>
    </div>
  );
}


export default async function Page({ params }: {
  params: {
    location: string,
    startDate: string,
    endDate: string
  }
}) {

  const trendingClubs = await getTrendingClubs() as TrendingClub[]
  const trendingComedians = await getTrendingComedians() as TrendingComedian[]
  const user = await getCurrentUser() as UserInterface;

  return (
    <LandingPage user={user} trendingComedians={trendingComedians} trendingClubs={trendingClubs} />
  )
}




