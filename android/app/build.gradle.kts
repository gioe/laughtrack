import java.io.FileInputStream
import java.util.Properties

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

// Release signing material. Local releases read a gitignored
// app/keystore.properties (storeFile/storePassword/keyAlias/keyPassword); CI
// reads the same values from environment variables injected from GitHub Actions
// secrets (see .github/workflows/android-release.yml). Both are optional so
// debug builds and `assembleRelease` on a machine without the upload key still
// configure cleanly — the signingConfig is only attached to the release build
// type when material is actually present (releaseSigningConfig below).
val keystorePropertiesFile = rootProject.file("app/keystore.properties")
val keystoreProperties =
    Properties().apply {
        if (keystorePropertiesFile.exists()) {
            FileInputStream(keystorePropertiesFile).use { load(it) }
        }
    }

fun signingValue(
    propKey: String,
    envKey: String,
): String? = keystoreProperties.getProperty(propKey) ?: System.getenv(envKey)

android {
    namespace = "app.laughtrack.android"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.laughtrack.android"
        minSdk = 26
        targetSdk = 35
        // Version source of truth is gradle.properties (VERSION_CODE / VERSION_NAME),
        // mirroring ios/project.yml's CURRENT_PROJECT_VERSION / MARKETING_VERSION split.
        // -PVERSION_CODE / -PVERSION_NAME override at build time so the Fastlane lane can
        // inject an auto-incremented Play build number without editing this file.
        versionCode = (project.findProperty("VERSION_CODE") as String?)?.toInt() ?: 1
        versionName = project.findProperty("VERSION_NAME") as String? ?: "0.1.0"

        // Custom runner swaps in HiltTestApplication so @HiltAndroidTest
        // instrumented tests (e.g. AppShellTest) get a real Hilt graph and can
        // render Hilt-backed destinations instead of crashing under a bare app.
        testInstrumentationRunner = "app.laughtrack.android.HiltTestRunner"

        // Deep-link / OAuth redirect scheme, mirrored from iOS (laughtrack://).
        manifestPlaceholders["appAuthRedirectScheme"] = "laughtrack"

        // Sentry DSN is empty by default so the SDK stays dormant; release builds
        // inject it via -PsentryDsn=... (CI secret). See LaughTrackApplication.
        buildConfigField("String", "SENTRY_DSN", "\"${project.findProperty("sentryDsn") ?: ""}\"")
    }

    // Resolve the release upload key once: storeFile path comes from
    // keystore.properties (local) or ANDROID_KEYSTORE_PATH (CI). keyPassword
    // defaults to the store password (the keystore generated for this app uses a
    // single password for both). When no material is present, releaseSigningName
    // stays null and the release build type is left unsigned (so a contributor
    // can still run `assembleRelease` locally without the upload key).
    val releaseStoreFile = signingValue("storeFile", "ANDROID_KEYSTORE_PATH")
    val releaseStorePassword = signingValue("storePassword", "ANDROID_KEYSTORE_PASSWORD")
    val releaseKeyAlias = signingValue("keyAlias", "ANDROID_KEY_ALIAS")
    val releaseKeyPassword = signingValue("keyPassword", "ANDROID_KEY_PASSWORD") ?: releaseStorePassword
    val hasReleaseSigning = releaseStoreFile != null && releaseStorePassword != null && releaseKeyAlias != null

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
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
            // Only attach the release signingConfig when signing material was
            // resolved above; otherwise leave it unsigned so local release builds
            // still configure. The Fastlane internal/production lanes always run
            // with material present, producing a signed AAB.
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
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
    androidTestImplementation(libs.hilt.android.testing)
    // fastlane screengrab: the instrumented AppStoreScreenshotTest calls
    // Screengrab.screenshot(...) to capture Play Store listing frames.
    androidTestImplementation(libs.fastlane.screengrab)
    kspAndroidTest(libs.hilt.compiler)
}
