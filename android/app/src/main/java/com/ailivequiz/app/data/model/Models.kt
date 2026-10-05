package com.ailivequiz.app.data.model

// ---------- Users ----------
data class UserCreateRequest(
    val email: String
)

data class UserResponse(
    val id: Int,
    val email: String
)

// ---------- Documents ----------
data class DocumentResponse(
    val id: Int,
    val filename: String,
    val status: String,
    val created_at: String
)

// ---------- Quiz generation ----------
data class QuizGenerateRequest(
    val document_id: Int,
    val num_questions: Int,
    val difficulty: String = "mixed", // "easy" | "medium" | "hard" | "mixed"
    val time_limit_minutes: Int = 10   // chosen directly by the user, like num_questions
)

data class OptionResponse(
    val option_index: Int,
    val option_text: String
)

data class QuestionResponse(
    val id: Int,
    val question_text: String,
    val options: List<OptionResponse>,
    val topic: String?,
    val difficulty: String?
)

data class QuizResponse(
    val id: Int,
    val quiz_number: Int,
    val num_questions: Int,
    val time_limit_seconds: Int,
    val questions: List<QuestionResponse>
)

// ---------- Attempts ----------
data class AttemptStartRequest(
    val quiz_id: Int,
    val user_id: Int
)

data class AttemptStartResponse(
    val attempt_id: Int,
    val quiz: QuizResponse
)

data class AnswerSubmit(
    val question_id: Int,
    val selected_option_index: Int
)

data class AttemptSubmitRequest(
    val answers: List<AnswerSubmit>
)

data class AnswerReview(
    val question_id: Int,
    val question_text: String,
    val selected_option_index: Int,
    val correct_option_index: Int,
    val is_correct: Boolean,
    val explanation: String?
)

data class AttemptResultResponse(
    val attempt_id: Int,
    val score: Int,
    val total_questions: Int,
    val percentage: Double,
    val answers: List<AnswerReview>
)

data class AttemptHistoryItem(
    val attempt_id: Int,
    val quiz_id: Int,
    val document_filename: String?,
    val quiz_number: Int?,
    val score: Int?,
    val total_questions: Int?,
    val completed_at: String?,
    val is_completed: Boolean
)

// ---------- V3: Performance Analytics ----------
data class TopicStat(
    val topic: String,
    val total_answered: Int,
    val correct: Int,
    val accuracy_percentage: Double,
    val is_weak: Boolean
)

data class OverviewStats(
    val total_attempts: Int,
    val total_questions_answered: Int,
    val total_correct: Int,
    val overall_accuracy_percentage: Double,
    val recent_attempts: List<AttemptHistoryItem>
)
