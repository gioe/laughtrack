import { getComedians } from "@/actions/getComedians";
import { getUpcomingShowResults } from "@/actions/getUpcomingShows";
import MediumComedianCard from "@/components/MediumComedianCard";
import SearchPageContents from "@/components/SearchPageContents";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import { UserInterface } from "@/interfaces/user.interface";
import moment from 'moment';
import Link from "next/link";

interface AllComediansPageProps {
    comedians: ComedianInterface[];
}

const AllComediansPage: React.FC<AllComediansPageProps> = async ({
    comedians,
}) => {
    return (
        <div>
        <main className="flex">
            <section className="flex-grow pt-14 px-6">
                <div className="flex flex-col">
                    {comedians.map((comedian: ComedianInterface) => {
                        return (
                            <Link href={comedian.name}>
                                <MediumComedianCard
                                    key={comedian.name}
                                    comedian={comedian}
                                />
                            </Link>
                        )
                    })}
                </div>

            </section>

        </main>
        </div>
    )
}

export default async function Page() {
    const comedians = await getComedians() as ComedianInterface[];

    return (
        <AllComediansPage
            comedians={comedians}
        />
    )
}
