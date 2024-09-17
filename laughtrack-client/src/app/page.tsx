import { getCurrentUser } from "@/actions/getCurrentUser";
import { getTrendingClubs } from "@/actions/getTrendingClubs";
import { getTrendingComics } from "@/actions/getTrendingComics";
import Banner from "@/components/Banner";
import ClientOnly from "@/components/ClientOnly";
import Footer from "@/components/Footer";
import MediumCard from "@/components/MediumCard";
import LoginModal from "@/components/modals/LoginModal";
import RegisterModal from "@/components/modals/RegisterModal";
import Navbar from "@/components/navbar/Navbar";
import SmallCard from "@/components/SmallCard";
import ToasterProvider from "@/providers/ToasterProvider";

export default async function Home() {

  const trendingClubs = await getTrendingClubs()
  const trendingComics = await getTrendingComics();
  const currentUser = await getCurrentUser();

  return (
    <div>
      <ClientOnly>
        <ToasterProvider />
        <LoginModal />
        <RegisterModal />
        <Navbar currentUser={currentUser} />
        <Banner />
        <main className="max-w-7xl mx-auto px-8 sm:px-16">
          <section className="pt-6">
            <h2 className="text-4xl font-semibold pb-5">Popular Clubs</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {trendingClubs.map((item: any) => {
              return (
                <SmallCard key={item.name} name={item.name} url={item.url} count={item.count} />
              )
            })}
            </div>
          </section>

          <section>
            <h2 className="text-4xl font-semibold py-8">Trending Comedians</h2>

            <div className="flex space-x-3 overflow-scroll scrollbar-hide">
            {trendingComics.map((item: any) => {
              return (
                <MediumCard key={item.name} name={item.name} instagram={item.instagram} count={item.count} />
              )
            })}
            </div>
          </section>
          
        </main>
        <Footer />
      </ClientOnly>
    </div>
  );
}

