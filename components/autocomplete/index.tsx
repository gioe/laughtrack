"use client";

import { Key } from "react";
import { FormField, FormItem, FormControl } from "../ui/form";
import { ControllerRenderProps, FieldValues } from "react-hook-form";

import { Autocomplete, AutocompleteItem } from "@nextui-org/react";
import { useAsyncList } from "@react-stately/data";
import axios from "axios";
import { useDebouncedCallback } from "use-debounce";
import { EntityType } from "../../objects/enum";
import { Entity } from "../../objects/interface";
import { Comedian } from "../../objects/class/comedian/Comedian";

type TypedFieldValues = ControllerRenderProps<FieldValues, string>;

interface AutocompleteFormComponentProps {
    type: EntityType;
    label: string;
    placeholder: string;
    name: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
}

export function AutocompleteFormComponent<T extends Entity>({
    label,
    form,
    name,
    placeholder,
    type,
}: AutocompleteFormComponentProps) {
    const handleSelection = (key: Key | null, field: TypedFieldValues) => {
        const comedian = JSON.parse(key as string) as Comedian;
        const chipData = {
            id: comedian.id,
            name: comedian.name,
        };
        const values = [...field.value, chipData];
        field.onChange(values);
    };

    const handleSearch = useDebouncedCallback(async (term) => {
        const response = await axios.post(`/api/search/${type.valueOf()}`, {
            body: {
                query: term,
            },
        });
        return { items: response.data.results };
    }, 300);

    const list = useAsyncList<T>({
        async load({ filterText }) {
            return handleSearch(filterText) ?? { items: [] };
        },
    });

    return (
        <FormField
            control={form.control}
            name={name}
            render={({ field }) => {
                return (
                    <FormItem>
                        <FormControl>
                            <Autocomplete
                                className="max-w-xs"
                                inputValue={list.filterText}
                                isLoading={list.isLoading}
                                items={list.items}
                                labelPlacement="outside"
                                label={label}
                                placeholder={placeholder}
                                variant="bordered"
                                onInputChange={list.setFilterText}
                                onSelectionChange={(key: Key | null) => {
                                    handleSelection(key, field);
                                }}
                            >
                                {(item) => {
                                    return (
                                        <AutocompleteItem
                                            key={JSON.stringify(item)}
                                            className="capitalize"
                                        >
                                            {item.name}
                                        </AutocompleteItem>
                                    );
                                }}
                            </Autocomplete>
                        </FormControl>
                    </FormItem>
                );
            }}
        />
    );
}
