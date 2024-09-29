
import { getComedianDetails } from "@/actions/getComedianDetails";

export default async function ComedianDetailsPage({ params }: { params: { id: string } }) {
  const { id } = params;

    const comedian = getComedianDetails(id)

    return (
        <div>
            
        </div>
    )
}
