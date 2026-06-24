package app.laughtrack.android.core.network.auth

import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import java.time.ZoneId

class AuthTokenInterceptor(
    private val tokenStore: TokenStore,
    private val timezoneProvider: () -> String = { ZoneId.systemDefault().id },
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val tokens = runBlocking { tokenStore.read() }
        val requestBuilder = chain.request().newBuilder()
            .header("X-Timezone", timezoneProvider())

        if (tokens?.accessToken?.isNotBlank() == true) {
            requestBuilder.header("Authorization", "Bearer ${tokens.accessToken}")
        }

        return chain.proceed(requestBuilder.build())
    }
}

