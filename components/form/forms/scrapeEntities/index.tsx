"use client";

import { useState } from "react";
import axios from "axios";
import { FormSelectable } from "../../../../objects/interface";
import { Club } from "../../../../objects/class/club/Club";
import { SelectComponent } from "../../../select";
import { CheckboxFormComponent } from "../../components/checkbox";
import { DropdownFormComponent } from "../../components/dropdown";
import BaseForm from "..";
import { ButtonType, EntityType } from "../../../../objects/enum";
import { scrapeEntitySelectionMenuSchema } from "./schema";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";

interface ScrapeEntitySelectionMenuFormProps {
    cities: FormSelectable[];
    type: EntityType;
    onSubmit: () => void;
}

export default function ScrapeEntitySelectionMenuForm({
    onSubmit,
    cities,
    type,
}: ScrapeEntitySelectionMenuFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const headlessOptions = [
        { id: "true", name: "True" },
        { id: "false", name: "False" },
    ] as FormSelectable[];

    const allCityOptions = [
        { id: "all", name: "All" } as FormSelectable,
    ].concat(cities);

    const [clubs, setClubs] = useState<FormSelectable[]>([]);

    const form = useForm<z.infer<typeof scrapeEntitySelectionMenuSchema>>({
        resolver: zodResolver(scrapeEntitySelectionMenuSchema),
        defaultValues: {
            entityType: type,
            ids: [],
            headless: true,
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
        let city = selection;

        if (selection == "all") {
            city = "";
            setClubs([]);
        }

        setIsLoading(true);
        axios
            .get(`/api/club/city/${city}`)
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    setClubs(
                        data.clubs.map((club: Club) => {
                            return {
                                value: club.name.toLowerCase(),
                                label: club.name,
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
                <div className="flex flex-col gap-4">
                    <SelectComponent
                        placeholder="Select city"
                        items={allCityOptions}
                        handleValueChange={handleCitySelection}
                    />
                    <CheckboxFormComponent
                        name="clubIds"
                        form={form}
                        items={clubs}
                    />
                    {clubs && (
                        <DropdownFormComponent
                            name="headless"
                            title="Headless"
                            form={form}
                            placeholder="Open browser window?"
                            items={headlessOptions}
                        />
                    )}
                </div>
            }
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "OK",
            }}
        />
    );
}
