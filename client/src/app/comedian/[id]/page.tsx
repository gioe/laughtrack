
import { getComedianDetails, GetComedianDetailsParams, GetComedianDetailsResponse } from "@/actions/comedians/getComedianDetails";
import ComedianBanner from "@/components/custom/banners/ComedianBanner";
import ShowTable from "@/components/custom/tables/ShowTable";

export default async function ComedianDetailsPage({
  params,
}: {
  params: GetComedianDetailsParams;
}) {

  const response = await getComedianDetails(params);

  return (
    <div>
      <section>
        <ComedianBanner
          comedian={response.entity}>
        </ComedianBanner>
      </section>
      <section>
        <ShowTable response={response} />
      </section>

    </div>
  )
}
