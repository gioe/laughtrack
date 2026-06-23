package app.laughtrack.android.core.network

import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

/**
 * Hilt module that will provide the OkHttp client, the generated OpenAPI service,
 * and the auth interceptors. Intentionally empty in the scaffold — the providers
 * land with TASK-3256 (generated client) and TASK-3257 (auth/session).
 */
@Suppress("unused")
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule
