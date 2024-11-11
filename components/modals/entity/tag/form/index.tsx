"use client";

import { TagInterface } from "../../../../../objects/interfaces";
import { CheckboxFormComponent } from "../../../../formComponents/checkbox";

interface TagEntityFormProps {
    tags: TagInterface[];
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function TagEntityForm({
    tags,
    form,
    name,
}: TagEntityFormProps) {
    const items = tags.map((tag: TagInterface) => {
        return {
            value: tag.id.toString(),
            label: tag.name,
        };
    });
    return (
        <div className="flex flex-col gap-4">
            <CheckboxFormComponent items={items} form={form} name={name} />
        </div>
    );
}
