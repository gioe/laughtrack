"use client";

import { useState, useEffect, useContext, createContext } from "react";
import axios from "axios";
import { CityDTO } from "../objects/class/city/city.interface";
import { RoutePath } from "../objects/enum";

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
        axios
            .get(RoutePath.GetCities)
            .then((response) => {
                return response.data;
            })
            .then((data) => {
                if (data) {
                    setCityList(data);
                }
            })
            .catch((error: Error) => {
                console.log(error);
            });
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
