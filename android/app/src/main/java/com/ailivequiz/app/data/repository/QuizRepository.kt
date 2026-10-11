package com.ailivequiz.app.data.repository

import com.ailivequiz.app.data.model.*
import com.ailivequiz.app.data.network.RetrofitInstance
import com.ailivequiz.app.data.network.TokenStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MultipartBody
import retrofit2.HttpException

/**
 * Every call is wrapped in a runCatching so ViewModels get a clean
 * Result<T> instead of having to catch IOException / HttpException
 * everywhere. HTTP error bodies (like the 502 "AI API call failed: ..."
 * detail from the backend) are surfaced as the exception message.
 */
class QuizRepository {

    private val api = RetrofitInstance.api

    // On success the token is stored straight away, so by the time the caller
    // sees the result every later request is already authenticated.
    suspend fun registerUser(username: String, email: String, password: String): Result<UserResponse> =
        safeCall { api.registerUser(UserRegisterRequest(username, email, password)) }
            .onSuccess { TokenStore.token = it.access_token }

    suspend fun loginUser(email: String, password: String): Result<UserResponse> =
        safeCall { api.loginUser(UserLoginRequest(email, password)) }
            .onSuccess { TokenStore.token = it.access_token }

    suspend fun uploadDocument(filePart: MultipartBody.Part): Result<DocumentResponse> =
        safeCall { api.uploadDocument(filePart) }

    suspend fun listDocuments(): Result<List<DocumentResponse>> = safeCall {
        api.listDocuments()
    }

    suspend fun getDocument(documentId: Int): Result<DocumentResponse> = safeCall {
        api.getDocument(documentId)
    }

    suspend fun generateQuiz(
        documentId: Int,
        numQuestions: Int,
        difficulty: String,
        timeLimitMinutes: Int
    ): Result<QuizResponse> = safeCall {
        api.generateQuiz(QuizGenerateRequest(documentId, numQuestions, difficulty, timeLimitMinutes))
    }

    suspend fun listQuizzesForDocument(documentId: Int): Result<List<QuizResponse>> = safeCall {
        api.listQuizzesForDocument(documentId)
    }

    suspend fun startAttempt(quizId: Int): Result<AttemptStartResponse> = safeCall {
        api.startAttempt(AttemptStartRequest(quizId))
    }

    suspend fun submitAttempt(
        attemptId: Int,
        answers: List<AnswerSubmit>
    ): Result<AttemptResultResponse> = safeCall {
        api.submitAttempt(attemptId, AttemptSubmitRequest(answers))
    }

    suspend fun getAttemptHistory(documentId: Int? = null): Result<List<AttemptHistoryItem>> = safeCall {
        api.getAttemptHistory(documentId)
    }

    /** Fetches a previously-completed attempt so the person can review it again later. */
    suspend fun getAttempt(attemptId: Int): Result<AttemptResultResponse> = safeCall {
        api.getAttempt(attemptId)
    }

    suspend fun getTopicStats(documentId: Int? = null): Result<List<TopicStat>> = safeCall {
        api.getTopicStats(documentId)
    }

    suspend fun getOverview(documentId: Int? = null): Result<OverviewStats> = safeCall {
        api.getOverview(documentId)
    }

    suspend fun getRecommendation(documentId: Int? = null): Result<RecommendationOut> = safeCall {
        api.getRecommendation(documentId)
    }

    private suspend fun <T> safeCall(block: suspend () -> T): Result<T> =
        withContext(Dispatchers.IO) {
            try {
                Result.success(block())
            } catch (e: HttpException) {
                // Try to surface the FastAPI {"detail": "..."} message rather
                // than a generic "HTTP 502" string.
                val errorBody = e.response()?.errorBody()?.string()
                val message = extractDetail(errorBody) ?: e.message() ?: "Server error (${e.code()})"
                Result.failure(Exception(message))
            } catch (e: CancellationException) {
                // A cancelled request (e.g. the user logged out mid-load) must
                // stop quietly - not be reported as an error message on screen.
                throw e
            } catch (e: Exception) {
                Result.failure(Exception(e.message ?: "Network error. Check your connection and backend URL."))
            }
        }

    private fun extractDetail(errorBody: String?): String? {
        if (errorBody.isNullOrBlank()) return null
        return try {
            val regex = "\"detail\"\\s*:\\s*\"(.*?)\"".toRegex()
            regex.find(errorBody)?.groupValues?.get(1)
        } catch (e: Exception) {
            null
        }
    }
}
