'use client'

import { Key, useState } from 'react';
import {
    FieldValues,
    SubmitHandler,
    useForm
} from 'react-hook-form'
import { useAsyncList } from "@react-stately/data";
import { Autocomplete, AutocompleteItem } from "@nextui-org/react";
import { Chip } from "@nextui-org/react";

import useAddComedianModal from '@/hooks/useAddComedianModal';
import Modal from './Modal';
import { useRouter } from 'next/navigation';
import { ComedianFilterInterface, ComedianInterface } from '@/interfaces/comedian.interface';
import { LineupItem } from '@/interfaces/lineupItem.interface';
import axios from 'axios';
import toast from 'react-hot-toast';
import { getPaginatedComedians } from '@/actions/comedians/getPaginatedComedians';
import Link from 'next/link';
import { ShowInterface } from '@/interfaces/show.interface';

interface AddComedianModalProps {
    show: ShowInterface
    intialComedians: LineupItem[]
}

const AddComedianModal: React.FC<AddComedianModalProps> = ({
    intialComedians, 
    show
}) => {

    const router = useRouter();

    let list = useAsyncList<LineupItem>({
        async load({ signal, filterText }) {
            let res = await getPaginatedComedians({
                query: filterText,
                sort: "alphabetical"
            })
            return {
                items: res.comedians
            };
        },
    });

    const { register, handleSubmit, formState } = useForm<FieldValues>();

    const addComedianModal = useAddComedianModal();

    const [isLoading, setIsLoading] = useState(false);
    const [comedians, setComedians] = useState(intialComedians);

    const handleSelection = (key: Key | null) => {
        if (key) {
            const selectedComedian = list.items.find(comedian => comedian.id == key)
            console.log(selectedComedian)
            var newComedians = comedians;
            if (selectedComedian) {
                newComedians.push(selectedComedian)
                setComedians(newComedians)
            }
        }
    };

    const handleClose = (item: LineupItem) => {
        setComedians(comedians.filter(comedian => comedian.name !== item.name));
    };

    const onSubmit: SubmitHandler<FieldValues> = (data) => {
        setIsLoading(true);
        console.log(comedians)

        axios.post('/api/addToLineup', {
            showId: show.id, 
            comedians: comedians.map((item: LineupItem) => item.id)
        })
            .then((response) => {
                if (response) {
                    setIsLoading(false)
                    toast.success("Successfully updated")
                    router.refresh();
                    addComedianModal.onClose();
                }
            })
    }

    const bodyContent = (
        <div className='flex flex-col gap-4'>
            <div className="grid grid-cols-3 gap-4">
                {comedians.map((comedian, index) => (
                    <Chip key={index} onClose={() => handleClose(comedian)} variant="flat">
                        {comedian.name}
                    </Chip>
                ))}
            </div>
            <Autocomplete
                className="max-w-xs"
                inputValue={list.filterText}
                isLoading={list.isLoading}
                items={list.items}
                labelPlacement='outside'
                label="Select a character"
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
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={addComedianModal.isOpen}
            title='Add Comedian'
            actionLabel='Continue'
            onClose={addComedianModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default AddComedianModal;