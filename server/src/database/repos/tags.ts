import {ColumnSet, IDatabase, IMain} from 'pg-promise';
import {tags as sql} from '../sql/index.js';
import { GetTagDTO, GetTagResponseDTO, TagShowDTO } from '../../common/models/interfaces/tag.interface.js';

var columnSets: {
    addAll: ColumnSet | null;
} = {
    addAll: null
}


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
    constructor(private db: IDatabase<any>, private pgp: IMain) {
          this.create();
          this.createClubTagsTable();
          this.createComedianTagsTable();
          this.createShowTagsTable();
          columnSets.addAll = new pgp.helpers.ColumnSet(['show_id', 'tag_id' ], {table: 'show_tags'});
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

    getAllByType(dto: GetTagDTO): Promise<GetTagResponseDTO[] | null> {
        return this.db.any(sql.getAllByType, {
            type: dto.type
        });
    }
    
    addAll(all: TagShowDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert)
    }

}