"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
    FormDirection,
    RoutePath,
    SortParamValue,
    URLParam,
} from "../../../../objects/enum";
import { usePathname, useRouter } from "next/navigation";
import { homeSearchSchema } from "./schema";
import { useState } from "react";
import { Navigator } from "../../../../objects/class/navigate/Navigator";
import { SearchParamsHelper } from "../../../../objects/class/params/SearchParamsHelper";
import BaseForm from "..";
import { CityInterface } from "../../../../objects/interface/city.interface";
import { FormSelectable } from "../../../../objects/interface";
import ShowSearchFormBody from "./body";
import { FormButton } from "../../components/button/home";

interface HomeSearchFormProps {
    cities: string;
}

export default function ShowSearchForm({ cities }: HomeSearchFormProps) {
    const selectableCities = (JSON.parse(cities) as CityInterface[]).map(
        (city: CityInterface) => {
            return {
                id: city.id,
                name: city.name,
            };
        },
    ) as FormSelectable[];

    const [isLoading, setIsLoading] = useState(false);

    const navigator = new Navigator(usePathname(), useRouter());

    const form = useForm<z.infer<typeof homeSearchSchema>>({
        resolver: zodResolver(homeSearchSchema),
        defaultValues: {
            cityId: "",
            dates: {
                from: undefined,
                to: undefined,
            },
        },
    });

    function submitForm(data: z.infer<typeof homeSearchSchema>) {
        setIsLoading(true);
        SearchParamsHelper.setParamValue(URLParam.City, data.cityId);
        SearchParamsHelper.setParamValue(URLParam.StartDate, data.dates.from);
        SearchParamsHelper.setParamValue(URLParam.EndDate, data.dates.to);
        SearchParamsHelper.setParamValue(URLParam.Sort, SortParamValue.Date);
        navigator.pushPageFromParams(
            RoutePath.ShowSearch,
            SearchParamsHelper.asParamsString(),
        );
    }

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            direction={FormDirection.Horizontal}
            body={
                <ShowSearchFormBody
                    selectableCities={selectableCities}
                    form={form}
                />
            }
            primaryButton={<FormButton label="Search" />}
        />
    );
}
