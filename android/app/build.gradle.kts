plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ktlint)
    alias(libs.plugins.detekt)
}

// Apply the Firebase google-services plugin only when a google-services.json is
// present. FCM needs a provisioned Firebase Android app (json downloaded into
// app/); until then the plugin is skipped so the build still compiles and runs —
// firebase-messaging's FirebaseInitProvider simply no-ops without the config.
if (file("google-services.json").exists()) {
    apply(plugin = libs.plugins.google.services.get().pluginId)
}

android {
    namespace = "app.laughtrack.android"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.laughtrack.android"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Deep-link / OAuth redirect scheme, mirrored from iOS (laughtrack://).
        manifestPlaceholders["appAuthRedirectScheme"] = "laughtrack"

        // Sentry DSN is empty by default so the SDK stays dormant; release builds
        // inject it via -PsentryDsn=... (CI secret). See LaughTrackApplication.
        buildConfigField("String", "SENTRY_DSN", "\"${project.findProperty("sentryDsn") ?: ""}\"")
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:navigation"))
    implementation(project(":core:network"))
    implementation(project(":core:data"))
    implementation(project(":core:playback"))
    implementation(project(":core:analytics"))
    implementation(project(":feature:home"))
    implementation(project(":feature:search"))
    implementation(project(":feature:library"))
    implementation(project(":feature:detail"))
    implementation(project(":feature:onboarding"))
    implementation(project(":feature:notifications"))
    implementation(project(":feature:profile"))

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.analytics)
    implementation(libs.sentry.android)

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.browser)
    implementation(libs.androidx.work.runtime.ktx)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)
    implementation(libs.androidx.navigation.compose)
    // Type-safe Navigation-Compose resolves @Serializable route serializers at runtime.
    implementation(libs.kotlinx.serialization.json)

    implementation(libs.hilt.android)
    implementation(libs.hilt.work)
    implementation(libs.hilt.navigation.compose)
    ksp(libs.hilt.compiler)
    ksp(libs.androidx.hilt.compiler)

    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}
