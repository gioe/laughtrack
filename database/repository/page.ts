import { IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { HomePageData, HomePageDTO } from '../../app/home/interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { Comedian } from '../../objects/class/comedian/Comedian';
import { pageDataMap } from '../sql';
import { QueryHelper } from '../../objects/class/query/QueryHelper';
import { ClubDetailDTO, ClubDetailPageData } from '../../app/club/[slug]/interface';
import { Club } from '../../objects/class/club/Club';
import { AllClubPageData, AllClubPageDTO } from '../../app/club/all/interface';
import { ClubDTO } from '../../objects/class/club/club.interface';
import { ComedianDetailDTO, ComedianDetailPageData } from '../../app/comedian/[slug]/interface';
import { AllComedianPageData, AllComedianPageDTO } from '../../app/comedian/all/interface';
import { AllShowPageData, AllShowPageDTO } from '../../app/show/all/interface';
import { ShowDTO } from '../../objects/class/show/show.interface';
import { Show } from '../../objects/class/show/Show';
import { ShowDetailDTO, ShowDetailPageData } from '../../app/show/[slug]/interface';
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

    async getHomePageData(): Promise<HomePageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.home, filters).then((data: HomePageDTO) => {
            return {
                cities: data.response.cities,
                comedians: data.response.comedians.map((dto: ComedianDTO) => new Comedian(dto))
            }
        })
    }

    async getComedianSearchPageData(): Promise<AllComedianPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.comedianSearch, filters).then((data: AllComedianPageDTO) => {
            return {
                entities: data.response.data.map((result: ComedianDTO) => new Comedian(result)),
                total: data.response.total
            }
        })
    }

    async getComedianDetailPageData(): Promise<ComedianDetailPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.comedianDetail, filters).then((data: ComedianDetailDTO) => {
            return {
                entity: new Comedian(data.response.data),
                total: data.response.total
            }
        })
    }

    async getClubSearchPageData(): Promise<AllClubPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.clubSearch, filters).then((data: AllClubPageDTO) => {
            return {
                entities: data.response.data.map((result: ClubDTO) => new Club(result)),
                total: data.response.total
            }
        })
    }

    async getClubDetailPageData(): Promise<ClubDetailPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.clubDetail, filters).then((data: ClubDetailDTO) => {
            return {
                entity: new Club(data.response.data),
                total: data.response.total
            }
        })
    }

    async getShowSearchPageData(): Promise<AllShowPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.showSearch, filters).then((data: AllShowPageDTO) => {
            return {
                entities: data.response.data.map((result: ShowDTO) => new Show(result)),
                total: data.response.total
            }
        })
    }

    async getShowDetailPageData(): Promise<ShowDetailPageData> {
        const filters = QueryHelper.asQueryFilters();

        return this.db.one(pageDataMap.showDetail, filters).then((data: ShowDetailDTO) => {
            return {
                entity: new Show(data.response.data),
                total: data.response.total
            }
        })
    }


}
