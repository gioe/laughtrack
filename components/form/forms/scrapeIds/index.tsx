"use client";

import { useState } from "react";
import axios from "axios";
import { Club } from "../../../../objects/class/club/Club";
import BaseForm from "..";
import { EntityType } from "../../../../objects/enum";
import { scrapeEntitySelectionMenuSchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import ScrapeEntitiesFormBody from "./body";
import { Selectable } from "../../../../objects/interface";

interface ScrapeEntitySelectionMenuFormProps {
    type: EntityType;
    onSubmit: () => void;
}

export default function ScrapeEntitySelectionMenuForm({
    onSubmit,
    type,
}: ScrapeEntitySelectionMenuFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const allCityOptions = [{ id: 0, value: "all", displayName: "All" }].concat(
        [],
    );

    const [clubs, setClubs] = useState<Selectable[]>([]);

    const form = useForm<z.infer<typeof scrapeEntitySelectionMenuSchema>>({
        resolver: zodResolver(scrapeEntitySelectionMenuSchema),
        defaultValues: {
            entityType: type,
            ids: [],
            headless: "true",
        },
    });

    const submitForm = (
        data: z.infer<typeof scrapeEntitySelectionMenuSchema>,
    ) => {
        setIsLoading(true);
        axios
            .post(`/api/${type.valueOf()}/scrape`, {
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
