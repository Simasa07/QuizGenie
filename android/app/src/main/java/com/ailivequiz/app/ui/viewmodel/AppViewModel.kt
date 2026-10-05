package com.ailivequiz.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ailivequiz.app.data.model.*
import com.ailivequiz.app.data.repository.QuizRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MultipartBody

/**
 * V1 has no login screen yet, so on first launch we silently create/reuse
 * a single demo user via POST /users/. Swap DEMO_EMAIL for a real
 * login flow in V2 without touching any other screen - they all just
 * read `userId` from here.
 */
private const val DEMO_EMAIL = "student@ailivequiz.local"

class AppViewModel : ViewModel() {

    private val repository = QuizRepository()

    private val _userId = MutableStateFlow<Int?>(null)
    val userId: StateFlow<Int?> = _userId.asStateFlow()

    private val _documents = MutableStateFlow<List<DocumentResponse>>(emptyList())
    val documents: StateFlow<List<DocumentResponse>> = _documents.asStateFlow()

    private val _currentQuiz = MutableStateFlow<QuizResponse?>(null)
    val currentQuiz: StateFlow<QuizResponse?> = _currentQuiz.asStateFlow()

    private val _currentAttemptId = MutableStateFlow<Int?>(null)
    val currentAttemptId: StateFlow<Int?> = _currentAttemptId.asStateFlow()

    private val _attemptResult = MutableStateFlow<AttemptResultResponse?>(null)
    val attemptResult: StateFlow<AttemptResultResponse?> = _attemptResult.asStateFlow()

    private val _history = MutableStateFlow<List<AttemptHistoryItem>>(emptyList())
    val history: StateFlow<List<AttemptHistoryItem>> = _history.asStateFlow()

    // Document-scoped insights: Insights only exists per-document (via the
    // Document Hub), there is no global Insights tab.
    private val _documentTopicStats = MutableStateFlow<List<TopicStat>>(emptyList())
    val documentTopicStats: StateFlow<List<TopicStat>> = _documentTopicStats.asStateFlow()

    private val _documentOverviewStats = MutableStateFlow<OverviewStats?>(null)
    val documentOverviewStats: StateFlow<OverviewStats?> = _documentOverviewStats.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    // questionId -> selectedOptionIndex, cleared whenever a new quiz starts
    private val _selectedAnswers = MutableStateFlow<Map<Int, Int>>(emptyMap())
    val selectedAnswers: StateFlow<Map<Int, Int>> = _selectedAnswers.asStateFlow()

    init {
        ensureDemoUser()
    }

    fun clearError() {
        _errorMessage.value = null
    }

    private fun ensureDemoUser() {
        viewModelScope.launch {
            _isLoading.value = true
            repository.createOrGetUser(DEMO_EMAIL)
                .onSuccess {
                    _userId.value = it.id
                    refreshDocuments()
                }
                .onFailure { _errorMessage.value = "Could not reach backend: ${it.message}" }
            _isLoading.value = false
        }
    }

    fun refreshDocuments() {
        val uid = _userId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            repository.listDocuments(uid)
                .onSuccess { _documents.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }

    fun uploadDocument(filePart: MultipartBody.Part, onDone: (DocumentResponse?) -> Unit) {
        val uid = _userId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            repository.uploadDocument(uid, filePart)
                .onSuccess {
                    refreshDocuments()
                    onDone(it)
                }
                .onFailure {
                    _errorMessage.value = it.message
                    onDone(null)
                }
            _isLoading.value = false
        }
    }

    fun generateQuiz(
        documentId: Int,
        numQuestions: Int,
        difficulty: String = "mixed",
        timeLimitMinutes: Int = 10,
        onDone: (QuizResponse?) -> Unit
    ) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.generateQuiz(documentId, numQuestions, difficulty, timeLimitMinutes)
                .onSuccess {
                    _currentQuiz.value = it
                    _selectedAnswers.value = emptyMap()
                    onDone(it)
                }
                .onFailure {
                    _errorMessage.value = it.message
                    onDone(null)
                }
            _isLoading.value = false
        }
    }

    fun startAttempt(quizId: Int, onDone: (Int?) -> Unit) {
        val uid = _userId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            repository.startAttempt(quizId, uid)
                .onSuccess {
                    _currentQuiz.value = it.quiz
                    _currentAttemptId.value = it.attempt_id
                    _selectedAnswers.value = emptyMap()
                    onDone(it.attempt_id)
                }
                .onFailure {
                    _errorMessage.value = it.message
                    onDone(null)
                }
            _isLoading.value = false
        }
    }

    fun selectAnswer(questionId: Int, optionIndex: Int) {
        _selectedAnswers.value = _selectedAnswers.value.toMutableMap().apply {
            put(questionId, optionIndex)
        }
    }

    fun submitAttempt(onDone: (AttemptResultResponse?) -> Unit) {
        val attemptId = _currentAttemptId.value ?: return
        val answers = _selectedAnswers.value.map { (questionId, index) ->
            AnswerSubmit(question_id = questionId, selected_option_index = index)
        }
        viewModelScope.launch {
            _isLoading.value = true
            repository.submitAttempt(attemptId, answers)
                .onSuccess {
                    _attemptResult.value = it
                    onDone(it)
                }
                .onFailure {
                    _errorMessage.value = it.message
                    onDone(null)
                }
            _isLoading.value = false
        }
    }

    /** Loads a past, already-completed attempt so it can be shown on the Result/Review screen. */
    fun loadAttemptResult(attemptId: Int, onDone: (AttemptResultResponse?) -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            _attemptResult.value = null // avoid flashing a stale previous result
            repository.getAttempt(attemptId)
                .onSuccess {
                    _attemptResult.value = it
                    onDone(it)
                }
                .onFailure {
                    _errorMessage.value = it.message
                    onDone(null)
                }
            _isLoading.value = false
        }
    }

    fun refreshHistory() {
        val uid = _userId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            repository.getAttemptHistory(uid)
                .onSuccess { _history.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }

    /** Loads topic breakdown + overview scoped to one document, for the per-PDF Insights screen. */
    fun refreshDocumentInsights(documentId: Int) {
        val uid = _userId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            _documentTopicStats.value = emptyList()
            _documentOverviewStats.value = null
            repository.getTopicStats(uid, documentId)
                .onSuccess { _documentTopicStats.value = it }
                .onFailure { _errorMessage.value = it.message }
            repository.getOverview(uid, documentId)
                .onSuccess { _documentOverviewStats.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }
}
