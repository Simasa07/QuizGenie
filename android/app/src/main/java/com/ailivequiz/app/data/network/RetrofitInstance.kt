package com.ailivequiz.app.data.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitInstance {

    /**
     * Physical phone over USB (current setup):
     *   1. Enable USB debugging on the phone and plug it in.
     *   2. Run once per cable connection:  adb reverse tcp:8000 tcp:8000
     *   3. 127.0.0.1:8000 on the phone now reaches your PC's port 8000.
     *
     * Other setups:
     * - Emulator: use "http://10.0.2.2:8000/"
     * - Phone over Wi-Fi: use "http://<your-PC-LAN-IP>:8000/" and start
     *   uvicorn with --host 0.0.0.0
     */
    private const val BASE_URL = "http://127.0.0.1:8000/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        // AI quiz generation can take a while (LLM call + validation),
        // so give it a generous timeout rather than failing fast.
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
