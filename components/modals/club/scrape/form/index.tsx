"use client";

import { DropdownFormComponent } from "../../../../formComponents/dropdown";
import Heading from "../../../heading";

interface ScrapeEntityFormProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function ScrapeEntityForm({ form }: ScrapeEntityFormProps) {
    const headlessOptions = [
        { value: "false", label: "False" },
        { value: "true", label: "True" },
    ];

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
