package com.ailivequiz.app.data.repository

import com.ailivequiz.app.data.model.*
import com.ailivequiz.app.data.network.RetrofitInstance
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

    suspend fun createOrGetUser(email: String): Result<UserResponse> = safeCall {
        api.createOrGetUser(UserCreateRequest(email))
    }

    suspend fun uploadDocument(userId: Int, filePart: MultipartBody.Part): Result<DocumentResponse> =
        safeCall { api.uploadDocument(userId, filePart) }

    suspend fun listDocuments(userId: Int): Result<List<DocumentResponse>> = safeCall {
        api.listDocuments(userId)
    }

    suspend fun getDocument(documentId: Int): Result<DocumentResponse> = safeCall {
        api.getDocument(documentId)
    }

    suspend fun generateQuiz(documentId: Int, numQuestions: Int): Result<QuizResponse> = safeCall {
        api.generateQuiz(QuizGenerateRequest(documentId, numQuestions))
    }

    suspend fun listQuizzesForDocument(documentId: Int): Result<List<QuizResponse>> = safeCall {
        api.listQuizzesForDocument(documentId)
    }

    suspend fun startAttempt(quizId: Int, userId: Int): Result<AttemptStartResponse> = safeCall {
        api.startAttempt(AttemptStartRequest(quizId, userId))
    }

    suspend fun submitAttempt(
        attemptId: Int,
        answers: List<AnswerSubmit>
    ): Result<AttemptResultResponse> = safeCall {
        api.submitAttempt(attemptId, AttemptSubmitRequest(answers))
    }

    suspend fun getAttemptHistory(userId: Int): Result<List<AttemptHistoryItem>> = safeCall {
        api.getAttemptHistory(userId)
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
