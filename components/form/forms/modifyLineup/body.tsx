/* eslint-disable @typescript-eslint/no-explicit-any */
import { Comedian } from "../../../../objects/class/comedian/Comedian";
import { EntityType } from "../../../../objects/enum";
import { AutocompleteFormComponent } from "../../components/autocomplete";
import { ChipFormComponent } from "../../components/chips";

interface ModifyLineupFormBodyProps {
    form: any;
}

export default function ModifyLineupFormBody({
    form,
}: ModifyLineupFormBodyProps) {
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
