"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ButtonType, RoutePath, URLParam } from "../../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { homeSearchSchema } from "./schema";
import { FormSelectable } from "../../../../objects/interface";
import { DropdownFormComponent } from "../../components/dropdown";
import { useState } from "react";
import { Navigator } from "../../../../objects/class/navigate/Navigator";
import { ParamsWrapper } from "../../../../objects/class/params/ParamsWrapper";
import BaseForm from "..";
import CalendarFormComponent from "../../components/calendar";

interface HomeSearchFormProps {
    citiesString: string;
}

export default function ShowSearchForm({ citiesString }: HomeSearchFormProps) {
    const cities = JSON.parse(citiesString) as FormSelectable[];
    const [isLoading /*setIsLoading*/] = useState(false);

    const paramsWrapper = ParamsWrapper.fromClientSideParams(useSearchParams());
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
        paramsWrapper.setParamValue(URLParam.City, data.cityId);
        paramsWrapper.setParamValue(URLParam.StartDate, data.dates.from);
        paramsWrapper.setParamValue(URLParam.EndDate, data.dates.to);
        navigator.pushPageFromParams(
            RoutePath.ShowSearchResults,
            paramsWrapper.asParamsString(),
        );
    }

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={
                <div
                    className="flex flex-col lg:flex-row lg:max-w-6xl
        lg:mx-auto items-start justify-center space-x-0 lg:space-x-2
        space-y-4 lg:space-y-0 rounded-lg"
                >
                    <DropdownFormComponent
                        name="cityId"
                        title="City"
                        placeholder="Select your city"
                        items={cities}
                        form={form}
                    />
                    <CalendarFormComponent name="dates" form={form} />
                </div>
            }
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "Search",
                styling: {
                    backgroundColor: "bg-silver-gray",
                },
            }}
        />
    );
}
