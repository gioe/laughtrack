"use client";

import { useState, useEffect, useContext, createContext } from "react";
import { CityDTO } from "../objects/class/city/city.interface";
import { APIRoutePath } from "../objects/enum";
import { executeGet } from "../util/actions/executeGet";

interface CityList {
    cities: CityDTO[];
}

const defaultList: CityList = {
    cities: [],
};

const CityContext = createContext<CityList>(defaultList);

export function CityProvider({ children }: { children: React.ReactNode }) {
    const [cityList, setCityList] = useState(defaultList);

    const getAffiliates = async () => {
        try {
            const response = await executeGet<Response>(APIRoutePath.City);

            if (!response.ok) {
                throw new Error("Failed to get cities");
            }

            const data = await response.json();

            if (data) {
                setCityList(data);
            }
        } catch (error) {
            console.log(error);
        }
    };

    useEffect(() => {
        getAffiliates();
    }, []);

    return (
        <CityContext.Provider value={cityList}>{children}</CityContext.Provider>
    );
}

export function useCityContext() {
    return useContext(CityContext);
}
