package app.laughtrack.android.core.network.generated.api

import app.laughtrack.android.core.network.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

import app.laughtrack.android.core.network.generated.model.ErrorResponse
import app.laughtrack.android.core.network.generated.model.ZipLookupResponse

interface GeoApi {
    /**
     * Resolve a US ZIP code to its city and state
     * Resolves a 5-digit US ZIP code to its city and state using the bundled &#x60;zipcodes&#x60; dataset. iOS clients call this to refine a manually entered ZIP into a city/state label without invoking CoreLocation.
     * Responses:
     *  - 200: ZIP resolved
     *  - 400: Missing or malformed ZIP
     *  - 404: ZIP not found in the dataset
     *  - 429: Rate limit exceeded
     *
     * @param zip 5-digit US ZIP code
     * @return [ZipLookupResponse]
     */
    @GET("zip-lookup")
    suspend fun lookupZip(@Query("zip") zip: kotlin.String): Response<ZipLookupResponse>

}
