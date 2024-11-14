"use client";

import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { Show } from "../../../../objects/class/show/Show";
import { ButtonType, EntityType } from "../../../../objects/enum";
import { AutocompleteFormComponent } from "../../components/autocomplete";
import { ChipFormComponent } from "../../components/chips";
import { useForm } from "react-hook-form";
import { addComedianToShowSchema } from "./schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import toast from "react-hot-toast";
import axios from "axios";
import BaseForm from "..";

interface AddComedianToShowFormProps {
    show: Show;
    onSubmit: () => void;
}

export default function AddComedianToShowForm({
    show,
    onSubmit,
}: AddComedianToShowFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const comedianChips = show.lineup.map((comedian: Comedian) => {
        return {
            id: comedian.id,
            name: comedian.name,
        };
    });

    const form = useForm<z.infer<typeof addComedianToShowSchema>>({
        resolver: zodResolver(addComedianToShowSchema),
        defaultValues: {
            showId: show.id,
            comedians: comedianChips,
        },
    });

    const submitForm = (data: z.infer<typeof addComedianToShowSchema>) => {
        setIsLoading(true);
        axios
            .post("/api/merge", {
                showId: data.showId,
                comedians: data.comedians,
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                }
            })
            .finally(onSubmit);
    };

    return (
        <BaseForm
            isLoading={isLoading}
            onSubmit={submitForm}
            form={form}
            body={
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-3 gap-4"></div>
                    <ChipFormComponent name="comedians" form={form} />
                    <AutocompleteFormComponent<Comedian>
                        type={EntityType.Comedian}
                        name="comedians"
                        label={"Search for a comedian"}
                        placeholder={"Type to search..."}
                        form={form}
                    />
                </div>
            }
            primaryButtonData={{
                type: ButtonType.Submit,
                label: "OK",
            }}
        />
    );
}
