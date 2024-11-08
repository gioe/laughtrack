"use client";

import useAddComedianModal from "../../../hooks/useAddComedianModal";
import Modal from "./Modal";
import toast from "react-hot-toast";
import axios from "axios";
import { Key, useState } from "react";
import { FieldValues, SubmitHandler, useForm } from "react-hook-form";
import { useAsyncList } from "@react-stately/data";
import { Autocomplete, AutocompleteItem } from "@nextui-org/react";
import { Chip } from "@nextui-org/react";
import { useRouter } from "next/navigation";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { executePost } from "../../../util/actions/executePost";
import { generateUrl } from "../../../util/primatives/urlUtil";
import { Comedian } from "../../../objects/classes/comedian/Comedian";
import { Show } from "../../../objects/classes/show/Show";
import { SortProperty } from "../../../util/enum";

interface AddComedianModalProps {
    show: Show;
    intialComedians: Comedian[];
}

const AddComedianModal: React.FC<AddComedianModalProps> = ({
    intialComedians,
    show,
}) => {
    const router = useRouter();

    const list = useAsyncList<Comedian>({
        async load({ filterText }) {
            const getComediansUrl = generateUrl(
                PUBLIC_ROUTES.GET_ALL_COMEDIANS,
            );
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const { items } = await executePost<any>(getComediansUrl, {
                query: filterText,
                sort: SortProperty.Alphabetical,
                page: "0",
                rows: "10",
            });
            return items.comedians;
        },
    });

    const { handleSubmit } = useForm<FieldValues>();

    const addComedianModal = useAddComedianModal();

    const [isLoading, setIsLoading] = useState(false);
    const [comedians, setComedians] = useState(intialComedians);

    const handleSelection = (key: Key | null) => {
        if (key) {
            const selectedComedian = list.items.find(
                (comedian) => comedian.id == key,
            );
            const newComedians = comedians;
            if (selectedComedian) {
                newComedians.push(selectedComedian);
                setComedians(newComedians);
            }
        }
    };

    const handleClose = (item: Comedian) => {
        setComedians(
            comedians.filter((comedian) => comedian.name !== item.name),
        );
    };

    const onSubmit: SubmitHandler<FieldValues> = () => {
        setIsLoading(true);

        axios
            .post("/api/addToLineup", {
                showId: show.id,
                comedians: comedians.map((item: Comedian) => item.id),
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    addComedianModal.onClose();
                }
            });
    };

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <div className="grid grid-cols-3 gap-4">
                {comedians.map((comedian, index) => (
                    <Chip
                        key={index}
                        onClose={() => handleClose(comedian)}
                        variant="flat"
                    >
                        {comedian.name}
                    </Chip>
                ))}
            </div>
            <Autocomplete
                className="max-w-xs"
                inputValue={list.filterText}
                isLoading={list.isLoading}
                items={list.items}
                labelPlacement="outside"
                label="Search for a comedian"
                placeholder="Type to search..."
                variant="bordered"
                onInputChange={list.setFilterText}
                onSelectionChange={handleSelection}
            >
                {(item) => (
                    <AutocompleteItem key={item.id} className="capitalize">
                        {item.name}
                    </AutocompleteItem>
                )}
            </Autocomplete>
        </div>
    );

    return (
        <Modal
            form={}
            disabled={isLoading}
            isOpen={addComedianModal.isOpen}
            title="Add Comedian"
            actionLabel="Continue"
            onClose={addComedianModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    );
};

export default AddComedianModal;
