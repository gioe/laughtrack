import { getDB } from "../../../database";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { EntityType } from "../../../util/enum";
import { Show } from "../../../objects/classes/show/Show";
import { getSortOptionsForEntityType } from "../../../util/sort";
import QueryableEntityTableContainer from "../../../components/container";
import ModifyLineupModal from "../../../components/modals/show/modifyLineup";
import ScrapeEntityModal from "../../../components/modals/entity/scrape";
import EntityBanner from "../../../components/banner";
import TagEntityModal from "../../../components/modals/entity/tag";

const { db } = getDB();

interface ShowDetailPageInterface {
    show: Show | null;
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
}) {
    const params = await props.params;
    const { show, tags } = await getShowDetail(params.id);
    const showString = JSON.stringify(show);
    const tagsString = JSON.stringify(tags);
    const responseString = JSON.stringify(show?.lineup ?? []);

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
                        <QueryableEntityTableContainer
                            sortOptions={getSortOptionsForEntityType(
                                EntityType.Comedian,
                            )}
                            responseString={responseString}
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
