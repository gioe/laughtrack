'use client'

import { useState } from 'react';
import {
    FieldValues,
    SubmitHandler,
    useForm
} from 'react-hook-form'

import useMergeComediansModal from '../../../hooks/useMergeComediansModal';
import Modal from './Modal';
import Heading from '../Heading';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import StylizedInput from '../inputs/StylizedInput';
import axios from 'axios';
import { ComedianInterface } from '../../../interfaces/comedian.interface';

interface MergeComediansModalParams {
    comedian?: ComedianInterface
}

const MergeComediansModal: React.FC<MergeComediansModalParams> = ({
    comedian
}) => {
    
    const mergeComediansModal = useMergeComediansModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const { register, handleSubmit, formState: {
        errors,
    }
    } = useForm<FieldValues>({
        defaultValues: {
            parentId: ""
        }
    });

    const onSubmit: SubmitHandler<FieldValues> = (data) => {
        setIsLoading(true);
        axios.post('/api/merge', {
            parentId: data.parentId,
            childId: comedian?.id
        })
            .then((response) => {
                if (response) {
                    setIsLoading(false)
                    toast.success("Successfully updated")
                    router.refresh();
                    mergeComediansModal.onClose();
                }
            })
    }

    const bodyContent = (
        <div className='flex flex-col gap-4'>
            <Heading
                title='Merge Comedians'
                subtitle='Merge comedian with a parent entity'
            />
            <StylizedInput
                id="parentId"
                label='Parent Id'
                disabled={isLoading}
                register={register}
                errors={errors}
            />
        </div>
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={mergeComediansModal.isOpen}
            title='Merge With Comedian'
            actionLabel='Continue'
            onClose={mergeComediansModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default MergeComediansModal;