import { getDB } from "../../../database";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import EntityBanner from "../../../components/banner";

import TagEntityModal from "../../../components/modals/entity/tag";
import { Show } from "../../../objects/classes/show/Show";
import { getSortOptionsForEntityType } from "../../../util/sort";
import QueryableTableContainer from "../../../components/container";
import ModifyLineupModal from "../../../components/modals/show/modifyLineup";
import ScrapeEntityModal from "../../../components/modals/entity/scrape";

const { db } = getDB();

interface ShowDetailPageInterface {
    show: Show | null;
    tags: TagInterface[];
}

async function getShowDetail(
    id: string,
    searchParams: SearchParams,
): Promise<ShowDetailPageInterface> {
    const show = db.shows.getById(Number(id), searchParams);
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
    const { show, tags } = await getShowDetail(params.id, searchParams);
    const showString = JSON.stringify(show);
    const tagsString = JSON.stringify(tags);
    const sortOptions = getSortOptionsForEntityType(EntityType.Comedian);

    return (
        <div>
            {show && (
                <main className="flex-grow pt-5 bg-shark">
                    <ScrapeEntityModal
                        entityId={show.id}
                        type={EntityType.Show}
                    />
                    <ModifyLineupModal showString={showString} />
                    <TagEntityModal
                        type={EntityType.Show}
                        entityId={show.id}
                        tagsString={tagsString}
                    />
                    <section>
                        <EntityBanner entityString={showString} />
                    </section>
                    <section>
                        <QueryableTableContainer
                            sortOptions={sortOptions}
                            resultString={JSON.stringify(show.lineup)}
                            defaultNode={
                                <h2 className="font-bold text-5xl text-white pt-6">
                                    No comedians on this show
                                </h2>
                            }
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
