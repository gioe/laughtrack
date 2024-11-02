import { Suspense } from "react";
import { ShowInterface } from "../../../interfaces/show.interface";
import { getDB } from "../../../database";
import { TagInterface } from "../../../interfaces/tag.interface";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import ComedianTable from "../../../components/custom/tables/ComedianTable";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import AddComedianModal from "../../../components/custom/modals/AddComedianModal";
import useAddShowTagModal from "../../../hooks/useAddShowTagModal";
import useAddComedianModal from "../../../hooks/useAddComedianModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";

const {db} = getDB();

const menuItems = [
    { key: "tags", label: "Add Tags", store: useAddShowTagModal },
    { key: "comedian", label: "Add Comedian", store: useAddComedianModal },
];

interface ShowDetailPageInterface {
    show: ShowInterface | null;
    tags: TagInterface[];
}

async function getShowDetail(id: string): Promise<ShowDetailPageInterface> {
    const show = db.shows.getById(Number(id));
    const tags = db.tags.getByType(EntityType.Show.valueOf());

    return Promise.all([show, tags]).then((responses) => {
        return {
            show: responses[0],
            tags: responses[1],
        };
    });
}

export default async function ShowDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;

    const { show, tags } = await getShowDetail(params.id);

    return (
        <div>
            {show && (
                <main className="flex-grow pt-5 bg-shark">
                    <AddComedianModal
                        show={show}
                        intialComedians={show.lineup}
                    />
                    <TagEntityModal
                        entity={show}
                        type={EntityType.Show}
                        tags={tags}
                    />
                    <section>
                        <EntityBanner entity={show} menuItems={menuItems} />
                    </section>
                    <section>
                        <Suspense
                            key={
                                (searchParams?.query ?? 1) +
                                (searchParams?.page ?? "")
                            }
                            fallback={<div />}
                        >
                            <ComedianTable params={searchParams} />
                        </Suspense>
                    </section>
                </main>
            )}
        </div>
    );
}
