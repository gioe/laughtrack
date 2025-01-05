/* eslint-disable @typescript-eslint/no-explicit-any */
import { IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { HomePageDataResponse } from '../../app/home/interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { Comedian } from '../../objects/class/comedian/Comedian';
import { pageDataMap } from '../sql';
import { Club } from '../../objects/class/club/Club';
import { ClubDTO } from '../../objects/class/club/club.interface';
import { ShowDTO } from '../../objects/class/show/show.interface';
import { Show } from '../../objects/class/show/Show';
import { ComedianDetailDTO, ComedianDetailPageData } from '../../app/(entities)/(detail)/comedian/[name]/interface';
import { ClubSearchData, ClubSearchDTO } from '../../app/(entities)/(collection)/club/all/interface';
import { ComedianSearchData, ComedianSearchDTO } from '../../app/(entities)/(collection)/comedian/all/interface';
import { ShowSearchData, ShowSearchDTO } from '../../app/(entities)/(collection)/show/all/interface';
import { ClubDetailDTO, ClubDetailPageData } from '../../app/(entities)/(detail)/club/[name]/interface';
import { DynamicRoute } from '../../objects/interface/identifable.interface';
import { EditComedianPageData } from '../../app/(entities)/(detail)/comedian/[name]/admin/interface';
import { EditClubPageData } from '../../app/(entities)/(detail)/club/[name]/admin/interface';


export class PageDataRepository {


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

    }

    async getHomePageData(userId?: string): Promise<HomePageDataResponse> {
        return this.db.one(pageDataMap.home, {
            userId: userId ? Number(userId) : null
        })
    }

    async getComedianSearchPageData(filters: any): Promise<ComedianSearchData> {
        return this.db.one(pageDataMap.comedianSearch, filters).then((data: ComedianSearchDTO) => {
            return {
                entities: data.response.data.map((result: ComedianDTO) => new Comedian(result)),
                total: data.response.total
            }
        })
    }

    async getComedianDetailPageData(filters: any): Promise<ComedianDetailPageData> {
        return this.db.one(pageDataMap.comedianDetail, filters).then((data: ComedianDetailDTO) => {
            return {
                entity: new Comedian(data.response.data),
                total: data.response.total
            }
        })
    }

    async getClubSearchPageData(filters: any): Promise<ClubSearchData> {
        return this.db.one(pageDataMap.clubSearch, filters).then((data: ClubSearchDTO) => {
            return {
                entities: data.response.data.map((result: ClubDTO) => new Club(result)),
                total: data.response.total
            }
        })
    }

    async getClubDetailPageData(filters: any): Promise<ClubDetailPageData> {
        return this.db.one(pageDataMap.clubDetail, filters).then((data: ClubDetailDTO) => {
            return {
                entity: new Club(data.response.data),
                total: data.response.total
            }
        })
    }

    async getShowSearchPageData(filters: any): Promise<ShowSearchData> {
        return this.db.one(pageDataMap.showSearch, filters).then((data: ShowSearchDTO) => {
            return {
                entities: data.response.data.map((result: ShowDTO) => new Show(result)),
                total: data.response.total
            }
        })
    }

    async getEditComedianDetailPageData(route: DynamicRoute): Promise<EditComedianPageData> {
        return this.db.one(pageDataMap.editComedian, {
            name: route.name
        }).then((value: any) => new Comedian(value))
    }

    async getEditClubDetailPageData(route: DynamicRoute): Promise<EditClubPageData> {
        return this.db.one(pageDataMap.editClub, {
            name: route.name
        }).then((value: any) => new Club(value))
    }

}
