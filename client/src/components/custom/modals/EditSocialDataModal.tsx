'use client'

import { useState } from 'react'; 
import { 
    FieldValues, 
    SubmitHandler,
    useForm
} from 'react-hook-form'

import useSocialDataModal from '@/hooks/useSocialDataModal';
import Modal from './Modal';
import Heading from '../Heading';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import StylizedInput from '../inputs/StylizedInput';

const EditSocialDataModal = () => {
    const router = useRouter();
    const socialDataModal = useSocialDataModal();

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
                title='Welcome back'
                subtitle='Login to your account'            
            />
            <StylizedInput 
                id="email" 
                label='Email' 
                disabled={isLoading} 
                register={register} 
                errors={errors} 
                required
            />
            <StylizedInput 
                id="password" 
                type='password'
                label='Password' 
                disabled={isLoading} 
                register={register} 
                errors={errors} 
                required
            />
        </div>
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={socialDataModal.isOpen}
            title='Edit Social Data'
            actionLabel='Continue'
            onClose={socialDataModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default EditSocialDataModal;