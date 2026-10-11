package com.ailivequiz.app.data.network

import com.ailivequiz.app.data.model.*
import okhttp3.MultipartBody
import retrofit2.http.*

interface ApiService {

    // ---------- Users ----------
    @POST("users/signup")
    suspend fun registerUser(@Body request: UserRegisterRequest): UserResponse

    @POST("users/login")
    suspend fun loginUser(@Body request: UserLoginRequest): UserResponse

    // ---------- Documents ----------
    // The backend knows who is uploading from the login token (added to every
    // request by RetrofitInstance), so there is no user_id parameter any more.
    @Multipart
    @POST("documents/upload")
    suspend fun uploadDocument(
        @Part file: MultipartBody.Part
    ): DocumentResponse

    @GET("documents/mine")
    suspend fun listDocuments(): List<DocumentResponse>

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

    @GET("attempts/mine")
    suspend fun getAttemptHistory(
        @Query("document_id") documentId: Int? = null
    ): List<AttemptHistoryItem>

    // ---------- Analytics (V3) ----------
    @GET("analytics/mine/topics")
    suspend fun getTopicStats(
        @Query("document_id") documentId: Int? = null
    ): List<TopicStat>

    @GET("analytics/mine/overview")
    suspend fun getOverview(
        @Query("document_id") documentId: Int? = null
    ): OverviewStats

    @GET("analytics/mine/recommendation")
    suspend fun getRecommendation(
        @Query("document_id") documentId: Int? = null
    ): RecommendationOut
}
