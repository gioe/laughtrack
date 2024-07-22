import { Comedian, User } from '@/util/types';
import { NextPageContext } from 'next';
import apiClient from "@/api/client"
import { AUTH_ENDPOINTS, COMEDIAN_ENDPOINTS } from '@/constants/endpoints';
export interface HomeProps {
  user: User,
  comedians: Comedian[]
}

const Home = () => {
  return (
    <main className="bg-[#1B262C]">
      <section>
        <h2 className="font-bold text-5xl text-white"> Find Your Next Stay </h2>
        <h2 className="text-white py-5 text-xl"> Search for low prices </h2>
      </section>
    </main>
  )
}

Home.getInitialProps = async (context: NextPageContext) => {
  const [userData, comediansData] = await Promise.all([
    await apiClient.get(AUTH_ENDPOINTS.currentUser).then(r => r.data.json()),
    await apiClient.get(COMEDIAN_ENDPOINTS.getAllComedians).then(r => r.data.json()),
  ]);
  return { user: userData, comedians: comediansData }
};


export default Home;