plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.ashu.app"
    // Platform 37 did not exist; 35 is a real, widely-installed platform.
    // Keep compileSdk >= targetSdk if you bump these.
    compileSdk = 35

    defaultConfig {
        applicationId = "com.ashu.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 8
        versionName = "0.8.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    buildFeatures {
        compose = true
    }

    // Keep Java and Kotlin on the same JVM target, otherwise AGP fails with
    // "Inconsistent JVM-target compatibility" (Java defaults to 1.8).
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    // v0.9: needed for the floating-companion overlay Service to host a
    // ComposeView (FloatingCompanion.kt) -- a Service is not itself a
    // LifecycleOwner/ViewModelStoreOwner/SavedStateRegistryOwner, so it has
    // to provide the ViewTree* owners those artifacts' extensions attach.
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("androidx.savedstate:savedstate-ktx:1.2.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")

    // ------------------------------------------------------------------
    // Optional on-device local model runtime.
    //
    // Ashu ships WITHOUT a bundled native runtime so the base APK stays small
    // and the build works with no extra repositories. To enable real local
    // inference, add a llama.cpp Android binding (e.g. a maintained
    // "llama-cpp-android" artifact) here and implement `LocalModelRunner` to
    // call it. The Python brain already speaks the same contract through
    // brain/inference.py, so no other layer changes.
    //
    // implementation("com.example:llama-cpp-android:<version>")
    // ------------------------------------------------------------------
}
