"use client";

import { useState } from "react";
import axios from "axios";
import { Club } from "../../../../objects/class/club/Club";
import BaseForm from "..";
import { scrapeEntitySelectionMenuSchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import ScrapeEntitiesFormBody from "./body";
import { Selectable } from "../../../../objects/interface";
import { EntityType } from "../../../../objects/enum";
import { useCityContext } from "../../../../contexts/CityProvider";
import { CityDTO } from "../../../../objects/class/city/city.interface";

interface ScrapeEntitySelectionMenuFormProps {
    onSubmit: () => void;
}

export default function ScrapeEntitySelectionMenuForm({
    onSubmit,
}: ScrapeEntitySelectionMenuFormProps) {
    const { cities } = useCityContext();
    const [isLoading, setIsLoading] = useState(false);

    const allCityOptions = [{ id: 0, value: "all", displayName: "All" }].concat(
        cities.map((city: CityDTO) => {
            return {
                id: city.id,
                value: city.name.toLowerCase(),
                displayName: city.name,
            };
        }),
    );

    const [clubs, setClubs] = useState<Selectable[]>([]);

    const form = useForm<z.infer<typeof scrapeEntitySelectionMenuSchema>>({
        resolver: zodResolver(scrapeEntitySelectionMenuSchema),
        defaultValues: {
            entityType: EntityType.Club,
            ids: [],
            headless: "true",
        },
    });

    const submitForm = (
        data: z.infer<typeof scrapeEntitySelectionMenuSchema>,
    ) => {
        setIsLoading(true);
        axios
            .post(`/api/${data.entityType.valueOf()}/scrape`, {
                ids: data.ids,
                headless: data.headless,
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setIsLoading(false);
                    toast.success(data.message);
                }
            })
            .finally(onSubmit);
    };

    const handleCitySelection = (selection: string) => {
        let cityId = selection;

        if (selection == "all") {
            cityId = "";
            setClubs([]);
        }

        setIsLoading(true);
        axios
            .get(`/api/club/city/${cityId}`)
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setClubs(
                        data.clubs.map((club: Club) => {
                            return {
                                id: club.id,
                                name: club.name,
                            };
                        }),
                    );
                    setIsLoading(false);
                }
            });
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={
                <ScrapeEntitiesFormBody
                    form={form}
                    handleCitySelection={handleCitySelection}
                    cityOptions={allCityOptions}
                    clubOptions={clubs}
                />
            }
        />
    );
}
