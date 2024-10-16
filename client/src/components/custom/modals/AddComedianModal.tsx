'use client'

import { useState } from 'react';
import {
    FieldValues,
    SubmitHandler,
    useForm
} from 'react-hook-form'
import { Select, SelectItem } from "@nextui-org/react";

import useAddComedianModal from '@/hooks/useAddComedianModal';
import Modal from './Modal';
import Heading from '../Heading';
import { useRouter } from 'next/navigation';
import { ComedianFilterInterface, ComedianInterface } from '@/interfaces/comedian.interface';
import { LineupItem } from '@/interfaces/lineupItem.interface';
import axios from 'axios';
import toast from 'react-hot-toast';

interface AddComedianModalProps {
    comedians: ComedianInterface[] | LineupItem[]
    filters: ComedianFilterInterface[]
}

const AddComedianModal: React.FC<AddComedianModalProps> = ({
    comedians,
    filters
}) => {
    const router = useRouter();
    const addComedianModal = useAddComedianModal();
    const [isLoading, setIsLoading] = useState(false);

    const { register, handleSubmit, formState: {
        errors,
    }
    } = useForm<FieldValues>({
        defaultValues: {
            email: '',
            password: ''
        }
    });

    const onSubmit: SubmitHandler<FieldValues> = (data) => {
        setIsLoading(true);

        axios.post('/api/addComedian', {
            ...data,
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
            <Heading
                title='Add'
                subtitle='Add comedian to show'
            />
            <Select
                label="Comedians"
                placeholder="Select a comedian"
                selectionMode="multiple"
                className="max-w-xs"
            >
                {filters.map((filter) => (
                    <SelectItem key={filter.id}>
                        {filter.name}
                    </SelectItem>
                ))}
            </Select>
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