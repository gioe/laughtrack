'use client'

import { signIn } from 'next-auth/react'
import { useState } from 'react'; 
import { 
    FieldValues, 
    SubmitHandler,
    useForm
} from 'react-hook-form'

import useLoginModal from '@/hooks/useLoginModal';
import Modal from './Modal';
import Heading from '../Heading';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';
import StylizedInput from '../inputs/StylizedInput';

const LoginModal = () => {
    const router = useRouter();
    const loginModal = useLoginModal();
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

        signIn('credentials', {
            ...data,
            redirect: false
        })
        .then((callback) => {
            setIsLoading(false)
            if (callback?.ok) {
                toast.success("Logged in")
                router.refresh();
                loginModal.onClose();
            }

            if (callback?.error) {
                toast.error(callback.error)
            }
        })
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
            isOpen={loginModal.isOpen}
            title='Login'
            actionLabel='Continue'
            onClose={loginModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
        />
    )
}

export default LoginModal;