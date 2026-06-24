plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
}

android {
    namespace = "app.laughtrack.android.core.navigation"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // Typed routes are @Serializable so Navigation-Compose (in :app) can use the
    // type-safe NavHost API. The route definitions, deep-link parser, and
    // cycle-dedup helper here are pure Kotlin — no Compose/Android-framework deps
    // — so they unit-test on the plain JVM without an emulator.
    implementation(libs.kotlinx.serialization.json)

    testImplementation(libs.junit)
}
