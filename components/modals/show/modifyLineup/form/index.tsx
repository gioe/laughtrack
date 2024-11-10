"use client";

import { Comedian } from "../../../../../objects/classes/comedian/Comedian";
import { Show } from "../../../../../objects/classes/show/Show";
import { ChipFormComponent } from "../../../../formComponents/chips";
import { AutocompleteFormComponent } from "../../../../formComponents/autocomplete";
import { EntityType } from "../../../../../util/enum";

interface AddComedianToShowFormProps {
    show: Show;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function AddComedianToShowForm({
    form,
}: AddComedianToShowFormProps) {
    return (
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
    );
}
