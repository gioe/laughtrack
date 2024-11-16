import { IDatabase, IMain } from "pg-promise";
import { map } from "../sql";
import {
    TagDTO,
    TagInterface,
} from "../../objects/interface";
import { IExtensions } from ".";
import { Tag } from "../../objects/class/tag/Tag";

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
        private db: IDatabase<IExtensions>,
        private pgp: IMain,
    ) { }

    createTable(): Promise<null> {
        return this.db.none(map.tag.createTable);
    }

    async getByType(type: string): Promise<TagInterface[]> {
        return this.db
            .any(map.tag.getByType, {
                type,
            })
            .then((response: TagDTO[] | null) =>
                response ? response.map((dto: TagDTO) => new Tag(dto)) : [],
            );
    }

}
