"use client";

import Heading from "../../heading";
import { Disclosure, DisclosurePanel } from "@headlessui/react";
import { FormSelectable } from "../../../../objects/interfaces";

interface TagEntityFormProps {
    checkboxOptions: FormSelectable[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export default function TagEntityForm({
    checkboxOptions,
    form,
}: TagEntityFormProps) {
    return (
        <div className="flex flex-col gap-4">
            <Heading title="Add" subtitle="Add tags to show" />
            <form className="lg:block">
                <Disclosure as="div" className="border-b border-gray-200 py-6">
                    <DisclosurePanel className="pt-6"></DisclosurePanel>
                    {checkboxOptions.length > 0 && (
                        <div className="space-y-4"></div>
                    )}
                </Disclosure>
            </form>
        </div>
    );
}
