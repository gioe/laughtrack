import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { tags as sql } from "../sql";
import {
    GetTagResponseDTO,
    TagClubDTO,
    TagComedianDTO,
    TagInterface,
    TagShowDTO,
} from "../../interfaces";
import { toTagInterfaceArray } from "../../util/domainModels/tag/mapper";

const columnSets: {
    addAllShowTags: ColumnSet | null;
    addAllComedianTags: ColumnSet | null;
    addAllClubTags: ColumnSet | null;
} = {
    addAllShowTags: null,
    addAllComedianTags: null,
    addAllClubTags: null,
};

export class TagsRepository {
    /**
     * @param db
     * Automated database connection context/interface.
     *
     * If you ever need to access other repositories from this one,
     * you will have to replace type 'IDatabase<any>' with 'any'.
     *
     * @param pgp
     * Library's root, if ever needed, like to access 'helpers'
     * or other namespaces available from the root.
     */
    constructor(
        private db: IDatabase<any>,
        private pgp: IMain,
    ) {
        columnSets.addAllShowTags = new pgp.helpers.ColumnSet(
            ["show_id", "tag_id"],
            { table: "show_tags" },
        );
        columnSets.addAllComedianTags = new pgp.helpers.ColumnSet(
            ["comedian_id", "tag_id"],
            { table: "comedian_tags" },
        );
        columnSets.addAllClubTags = new pgp.helpers.ColumnSet(
            ["club_id", "tag_id"],
            { table: "club_tags" },
        );
    }

    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Creates the table;
    createClubTagsTable(): Promise<null> {
        return this.db.none(sql.createClubTags);
    }

    createComedianTagsTable(): Promise<null> {
        return this.db.none(sql.createComedianTags);
    }

    createShowTagsTable(): Promise<null> {
        return this.db.none(sql.createShowTags);
    }

    async getByType(type: string): Promise<TagInterface[]> {
        return this.db
            .any(sql.getAllByType, {
                type,
            })
            .then((response: GetTagResponseDTO[] | null) =>
                response ? toTagInterfaceArray(response) : [],
            );
    }

    addAllShowTags(all: TagShowDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAllShowTags) +
            ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert);
    }

    addAllComedianTags(all: TagComedianDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAllComedianTags) +
            ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert);
    }

    addAllClubTags(all: TagClubDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAllClubTags) +
            ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert);
    }
}
