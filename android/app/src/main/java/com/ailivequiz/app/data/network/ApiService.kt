package com.ailivequiz.app.data.network

import com.ailivequiz.app.data.model.*
import okhttp3.MultipartBody
import retrofit2.http.*

interface ApiService {

    // ---------- Users ----------
    @POST("users/")
    suspend fun createOrGetUser(@Body request: UserCreateRequest): UserResponse

    // ---------- Documents ----------
    // user_id is a query param here because that's how FastAPI treats a plain
    // int parameter alongside a File(...) param (see documents.py).
    @Multipart
    @POST("documents/upload")
    suspend fun uploadDocument(
        @Query("user_id") userId: Int,
        @Part file: MultipartBody.Part
    ): DocumentResponse

    @GET("documents/user/{userId}")
    suspend fun listDocuments(@Path("userId") userId: Int): List<DocumentResponse>

    @GET("documents/{documentId}")
    suspend fun getDocument(@Path("documentId") documentId: Int): DocumentResponse

    // ---------- Quizzes ----------
    @POST("quizzes/generate")
    suspend fun generateQuiz(@Body request: QuizGenerateRequest): QuizResponse

    @GET("quizzes/{quizId}")
    suspend fun getQuiz(@Path("quizId") quizId: Int): QuizResponse

    @GET("quizzes/document/{documentId}")
    suspend fun listQuizzesForDocument(@Path("documentId") documentId: Int): List<QuizResponse>

    // ---------- Attempts ----------
    @POST("attempts/start")
    suspend fun startAttempt(@Body request: AttemptStartRequest): AttemptStartResponse

    @POST("attempts/{attemptId}/submit")
    suspend fun submitAttempt(
        @Path("attemptId") attemptId: Int,
        @Body request: AttemptSubmitRequest
    ): AttemptResultResponse

    @GET("attempts/{attemptId}")
    suspend fun getAttempt(@Path("attemptId") attemptId: Int): AttemptResultResponse

    @GET("attempts/user/{userId}")
    suspend fun getAttemptHistory(@Path("userId") userId: Int): List<AttemptHistoryItem>
}
