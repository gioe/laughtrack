'use client'

import { useState } from 'react'; 
import Modal from './Modal';
import Heading from '../Heading';
import toast from 'react-hot-toast';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import useClearShowsModal from '@/hooks/useClearShowsModal';
import { ShowProviderInterface } from '@/interfaces/showProvider.interface';

interface ClearShowsModalParams {
    clubId: number
}

const ClearShowsModal: React.FC<ClearShowsModalParams> = ({
    clubId
}) => {
    const clearShowsModal = useClearShowsModal();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);


    const handleSubmit = () => {
        setIsLoading(true);
        axios.post('/api/clear', {
            id: clubId,
        })
            .then((response) => {
                if (response) {
                    setIsLoading(false)
                    toast.success("Successfully updated")
                    router.refresh();
                    clearShowsModal.onClose();
                 }
            })
    }


    const bodyContent = (
        <div className='flex flex-col gap-4'>
            <Heading
                title='Clear Shows'
            />
        </div>
    )

    return (
        <Modal
            disabled={isLoading}
            isOpen={clearShowsModal.isOpen}
            title='Clear'
            actionLabel='Continue'
            onClose={clearShowsModal.onClose}
            onSubmit={handleSubmit}
            body={bodyContent}
        />
    )
}

export default ClearShowsModal;