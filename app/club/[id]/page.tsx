import { ClubInterface } from "../../../interfaces/club.interface";
import { TagInterface } from "../../../interfaces/tag.interface";
import { Suspense } from "react";
import { Paginated } from "../../..//interfaces/paginated.interface";
import { SORT_OPTIONS } from "../../../util/sort";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import FilterPageContainer from "../../..//components/custom/filters/FilterPageContainer";
import ClearShowsModal from "../../..//components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "../../..//components/custom/modals/ScrapeClubModal";
import ShowTable from "../../..//components/custom/tables/ShowTable";
import useAddClubTagModal from "../../..//hooks/useAddClubTagModal";
import useRunScrapeModal from "../../..//hooks/useRunScrapeModal";
import useClearShowsModal from "../../..//hooks/useClearShowsModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";

const {db} = getDB();

const menuItems = [
    { key: "tags", label: "Add Tags", store: useAddClubTagModal },
    { key: "scrape", label: "Run Scrape", store: useRunScrapeModal },
    { key: "clear", label: "Clear SHows", store: useClearShowsModal },
];

interface ClubDetailPageInterface extends Paginated {
    club: ClubInterface | null;
    tags: TagInterface[];
}

async function getClubDetail(id: string): Promise<ClubDetailPageInterface> {
    const club = db.clubs.getByName(id);
    const tags = db.tags.getByType(EntityType.Club.valueOf());

    return Promise.all([club, tags]).then((responses) => {
        const club = responses[0];
        const tags = responses[1];
        return {
            club,
            totalResults: club?.dates.length ?? 0,
            tags,
        };
    });
}

export default async function ClubDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;
    const { tags, club, totalResults } = await getClubDetail(params.id);

    return (
        <div>
            {club && (
                <main className="flex-grow pt-5 bg-shark">
                    <ScrapeClubModal club={club} />
                    <ClearShowsModal club={club} />
                    <TagEntityModal
                        entity={club}
                        type={EntityType.Club}
                        tags={tags}
                    />
                    <section>
                        <EntityBanner entity={club} menuItems={menuItems} />
                    </section>
                    <section>
                        <FilterPageContainer
                            itemCount={totalResults}
                            sortOptions={SORT_OPTIONS.CLUB}
                            child={
                                <Suspense
                                    key={
                                        (searchParams?.query ?? 1) +
                                        (searchParams?.page ?? "")
                                    }
                                    fallback={<div />}
                                >
                                    <ShowTable params={searchParams} />
                                </Suspense>
                            }
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
