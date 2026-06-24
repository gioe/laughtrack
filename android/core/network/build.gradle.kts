plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
}

android {
    namespace = "app.laughtrack.android.core.network"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
        // Base URL of the shared /api/v1 backend (parity with iOS AppConfiguration).
        buildConfigField("String", "API_BASE_URL", "\"https://www.laugh-track.com/api/v1/\"")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    // Networking stack populated by the OpenAPI-client task (TASK-3256) and the
    // auth/session task (TASK-3257). Declared here so module wiring is ready.
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    // api(), not implementation(): the generated Retrofit interfaces in
    // generated/api/*.kt return retrofit2.Response<T>, so retrofit2.Response is
    // part of this module's public ABI. Consumers (:core:data, :feature:search)
    // that call those APIs need it on their compile classpath transitively.
    api(libs.retrofit)
    // Converters required by the generated Retrofit client (api/ infrastructure):
    // scalars for raw String/primitive bodies, kotlinx-serialization for JSON.
    implementation(libs.retrofit.converter.scalars)
    implementation(libs.retrofit.converter.kotlinx.serialization)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.androidx.security.crypto)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
}
