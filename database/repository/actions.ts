/* eslint-disable @typescript-eslint/no-explicit-any */
import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { apiActionMap } from '../sql';
import { UserDTO } from '../../objects/interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { DynamicRoute } from '../../objects/interface/identifable.interface';
import { AddFavoriteDTO } from '../../objects/interface/favoritable.interface';

const columnSets: {
    addComedianTags: ColumnSet | null;
} = {
    addComedianTags: null,
}

export class ActionRepository {

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
    constructor(private db: IDatabase<IExtensions>, private pgp: IMain) {
        columnSets.addComedianTags = new pgp.helpers.ColumnSet(['comedian_id', 'tag_id'], { table: 'tagged_comedians' });
    }

    async deleteShowsForClub(id: any): Promise<any[]> {
        return this.db.any(apiActionMap.deleteShows, {
            id
        })
    }

    async addUser(user: UserDTO): Promise<any> {
        return this.db.one(apiActionMap.addUser, {
            email: user.email,
            role: user.role,
            password: user.password
        });
    }

    async addComedian(comedian: ComedianDTO): Promise<any> {
        return this.db.one(apiActionMap.addComedian, {
            name: comedian.name,
            uuid: comedian.uuid,
        });
    }

    async addFavorite(favoriteDto: AddFavoriteDTO): Promise<any> {
        if (!favoriteDto.is_favorite) {
            return this.db.one(apiActionMap.addFavorite, {
                comedianId: favoriteDto.comedian_id,
                userId: favoriteDto.user_id,
            });
        } else {
            return this.db.one(apiActionMap.deleteFavorite, {
                comedianId: favoriteDto.comedian_id,
                userId: favoriteDto.user_id,
            });
        }
    }


    async updateComedian(slug: DynamicRoute, args: any): Promise<any> {
        if (args.ids.length > 0) {
            const allTags = args.ids.map((id: number) => {
                return {
                    'tag_id': id,
                    'comedian_id': args.id
                }
            })
            const batchInsert = this.pgp.helpers.insert(allTags, columnSets.addComedianTags) + ' ON CONFLICT DO NOTHING';
            await this.db.any(batchInsert)
        }

        return this.db.none(apiActionMap.updateComedian, {
            linktree: args.linktree,
            instagram_account: args.instagram.account,
            instagram_followers: args.instagram.following == '' ? 0 : Number(args.instagram.following),
            tiktok_account: args.tiktok.account,
            tiktok_followers: args.tiktok.following == '' ? 0 : Number(args.tiktok.following),
            youtube_account: args.youtube.account,
            youtube_followers: args.youtube.following == '' ? 0 : Number(args.youtube.following),
            website: args.website,
            name: slug.name
        });
    }


}
