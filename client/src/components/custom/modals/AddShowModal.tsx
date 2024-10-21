'use client'

import { useState } from 'react'; 
import { 
    FieldValues, 
    SubmitHandler,
    useForm
} from 'react-hook-form'

import useAddShowModal from '@/hooks/useAddShowsModal';
import Modal from './Modal';
import Heading from '../Heading';
import { useRouter } from 'next/navigation';
import { ShowProviderInterface } from '@/interfaces/showProvider.interface';

interface AddShowModalProps {
    entity?: ShowProviderInterface
}


const AddShowModal: React.FC<AddShowModalProps> = ({
    entity
}) => {
    const router = useRouter();
    const addShowModal = useAddShowModal();

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

    }
    
    const bodyContent = (
        <div className='flex flex-col gap-4'>
            <Heading
                title='Add show'
                subtitle='Add show to club schedule'            
            />
        </div>
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={addShowModal.isOpen}
            title='Add Show'
            actionLabel='Continue'
            onClose={addShowModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default AddShowModal;