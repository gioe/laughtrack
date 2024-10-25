'use client'

import { useState } from 'react';
import {
    FieldValues,
    SubmitHandler,
    useForm
} from 'react-hook-form'
import Modal from './Modal';
import Heading from '../Heading';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { TagInterface } from '@/interfaces/tag.interface';
import { Disclosure, DisclosurePanel } from '@headlessui/react';
import { FilterOption } from '../filters/FilterPageContainer';
import { ShowProviderInterface } from '@/interfaces/showProvider.interface';
import useAddComedianTagModal from '@/hooks/useAddComedianTagModal';
import { ComedianInterface } from '@/interfaces/comedian.interface';

interface AddComediantagModalProps {
    comedian: ComedianInterface
    tags: TagInterface[]
}

const AddComedianTagModal: React.FC<AddComediantagModalProps> = ({
    comedian,
    tags
}) => {

    const router = useRouter();
    const addComedianTagModal = useAddComedianTagModal();
    const [isLoading, setIsLoading] = useState(false);
    const [selectedTags, setSelectedTags] = useState(comedian.tags ? comedian.tags.map((tag: TagInterface) => tag.id) : []);

    const { handleSubmit } = useForm<FieldValues>();

    const handleSelection = (value: string) => {
        const valueNumber = Number(value)
        let newTags = selectedTags
        const existingTag = selectedTags.find((id: number) => id == valueNumber)

        if (existingTag) {
            newTags = newTags.filter((id: number) => id !== valueNumber)
        } else {
            newTags.push(valueNumber)
        }

        setSelectedTags(newTags)

    }

    const filterOptions: FilterOption[] = tags.map((item: TagInterface) => {
        const tag = selectedTags.find((tag: number) => tag == item.id)
        return {
            value: item.id.toString(),
            label: item.name,
            selected: tag ? true : false
        }
    })

    const onSubmit: SubmitHandler<FieldValues> = () => {
        setIsLoading(true);

        axios.post('/api/comedian/addTag', {
            comedianId: comedian.id,
            tags: selectedTags
        })
            .then((response) => {
                if (response) {
                    setIsLoading(false)
                    toast.success("Successfully updated")
                    router.refresh();
                    addComedianTagModal.onClose();
                }
            })
    }

    const bodyContent = (
        <div className='flex flex-col gap-4'>
            <Heading
                title='Add'
                subtitle='Add tags to show'
            />
            <form className="lg:block">
                <Disclosure as="div" className="border-b border-gray-200 py-6">
                    <DisclosurePanel className="pt-6">

                    </DisclosurePanel>
                    {tags.length > 0 &&
                        <div className="space-y-4">
                            {filterOptions.map((option, optionIdx) => (
                                <div key={option.value} className="flex items-center">
                                    <input
                                        onClick={() => handleSelection(option.value)}
                                        defaultValue={option.value}
                                        defaultChecked={option.selected}
                                        id={`filter-${option.value}-${optionIdx}`}
                                        name={`${option.value}[]`}
                                        type="checkbox"
                                        className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                    />
                                    <label htmlFor={`filter-${option.value}-${optionIdx}`} className="ml-3 text-sm text-gray-600">
                                        {option.label}
                                    </label>
                                </div>
                            ))}
                        </div>
                    }
                </Disclosure>

            </form>
        </div>
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={addComedianTagModal.isOpen}
            title='Add Tags'
            actionLabel='Continue'
            onClose={addComedianTagModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default AddComedianTagModal;