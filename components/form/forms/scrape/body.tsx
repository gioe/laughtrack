/* eslint-disable @typescript-eslint/no-explicit-any */
import { FormSelectable } from "../../../../objects/interface";
import Heading from "../../../modals/heading";
import { DropdownFormComponent } from "../../components/dropdown";

interface ScrapeEntityFormBodyProps {
    form: any;
    headlessOptions: FormSelectable[];
}

export default function ScrapeEntityFormBody({
    form,
    headlessOptions,
}: ScrapeEntityFormBodyProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Scrape Club" />
            <DropdownFormComponent
                name="headless"
                title="Headless"
                form={form}
                placeholder="Open browser window?"
                items={headlessOptions}
            />
        </div>
    );
}
