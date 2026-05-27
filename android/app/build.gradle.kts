plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")
    id("dagger.hilt.android.plugin")
}

android {
    namespace = "io.eosim.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.eosim.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 301
        versionName = "3.0.1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Production API endpoints — never use localhost
        buildConfigField("String", "API_BASE_URL", "\"https://api.eosim.io\"")
        buildConfigField("String", "WS_BASE_URL", "\"wss://api.eosim.io\"")
        buildConfigField("String", "DOCS_URL", "\"https://docs.eosim.io\"")
        buildConfigField("String", "STATUS_URL", "\"https://status.eosim.io\"")
        buildConfigField("String", "APP_URL", "\"https://app.eosim.io\"")
        buildConfigField("String", "CDN_URL", "\"https://cdn.eosim.io\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("release")
        }
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
            buildConfigField("String", "API_BASE_URL", "\"https://api.eosim.io\"")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // Compose BOM
    val composeBom = platform("androidx.compose:compose-bom:2024.02.00")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.7")

    // Core Android
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")

    // Networking — Production API
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // WebSocket — wss://api.eosim.io
    implementation("org.java-websocket:Java-WebSocket:1.5.4")

    // DI
    implementation("com.google.dagger:hilt-android:2.50")
    kapt("com.google.dagger:hilt-compiler:2.50")

    // Location / GPS
    implementation("com.google.android.gms:play-services-location:21.1.0")

    // i18n / Localization
    implementation("androidx.appcompat:appcompat:1.6.1")

    // Biometric
    implementation("androidx.biometric:biometric:1.1.0")

    // Charts
    implementation("com.patrykandpatrick.vico:compose-m3:1.13.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("io.mockk:mockk:1.13.9")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation(composeBom)
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
