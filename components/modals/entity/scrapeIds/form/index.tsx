"use client";

import { useState } from "react";
import { CheckboxFormComponent } from "../../../../formComponents/checkbox";
import axios from "axios";
import { DropdownFormComponent } from "../../../../formComponents/dropdown";
import { FormSelectable } from "../../../../../objects/interfaces";
import { Club } from "../../../../../objects/classes/club/Club";
import { SelectComponent } from "../../../../select";

interface ScrapeEntitySelectionMenuFormProps {
    cities: FormSelectable[];
    handleLoadingState: (loading: boolean) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function ScrapeEntitySelectionMenuForm({
    handleLoadingState,
    cities,
    form,
}: ScrapeEntitySelectionMenuFormProps) {
    const headlessOptions = [
        { id: "true", name: "True" },
        { id: "false", name: "False" },
    ] as FormSelectable[];

    const allCityOptions = [
        { id: "all", name: "All" } as FormSelectable,
    ].concat(cities);

    const [clubs, setClubs] = useState<FormSelectable[]>([]);

    const handleCitySelection = (selection: string) => {
        let city = selection;

        if (selection == "all") {
            city = "";
            setClubs([]);
        }

        handleLoadingState(true);
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
                    handleLoadingState(false);
                }
            });
    };

    return (
        <div className="flex flex-col gap-4">
            <SelectComponent
                placeholder="Select city"
                items={allCityOptions}
                handleValueChange={handleCitySelection}
            />
            <CheckboxFormComponent name="clubIds" form={form} items={clubs} />
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
    );
}
