/* eslint-disable @typescript-eslint/no-explicit-any */
import { EntityType } from "../../../../objects/enum";
import { COMMON_OPTIONS } from "../../../../util/form";
import Heading from "../../../modals/heading";
import { DropdownFormComponent } from "../../components/dropdown";

interface ScrapeEntityFormBodyProps {
    form: any;
    type: EntityType;
}

export default function ScrapeEntityFormBody({
    form,
    type,
}: ScrapeEntityFormBodyProps) {
    return (
        <div className="flex flex-col items-center gap-4">
            <Heading title="Scrape Club" />
            <DropdownFormComponent
                name="headless"
                title="Headless"
                form={form}
                placeholder="Open browser window?"
                items={COMMON_OPTIONS.YesNo}
            />
            {type == EntityType.Show && (
                <DropdownFormComponent
                    name="pause"
                    title="Pause"
                    form={form}
                    placeholder="Pause browser window?"
                    items={COMMON_OPTIONS.YesNo}
                />
            )}
        </div>
    );
}
