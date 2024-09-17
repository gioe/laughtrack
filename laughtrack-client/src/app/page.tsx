import { getCurrentUser } from "@/actions/getCurrentUser";
import { getTrendingClubs } from "@/actions/getTrendingClubs";
import { getTrendingComics } from "@/actions/getTrendingComics";
import Banner from "@/components/Banner";
import ClientOnly from "@/components/ClientOnly";
import LoginModal from "@/components/modals/LoginModal";
import RegisterModal from "@/components/modals/RegisterModal";
import Navbar from "@/components/navbar/Navbar";
import { PUBLIC_ROUTES } from "@/lib/routes";
import ToasterProvider from "@/providers/ToasterProvider";
import { error } from "console";
import { useEffect, useState } from "react";


export default async function Home() {

  const trendingClubs = await getTrendingClubs()
  // const trendingComics = await getTrendingComics();
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
          </section>
        </main>
      </ClientOnly>
    </div>
  );
}

