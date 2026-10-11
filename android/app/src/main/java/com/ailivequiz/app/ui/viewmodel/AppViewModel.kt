package com.ailivequiz.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ailivequiz.app.data.model.*
import com.ailivequiz.app.data.network.TokenStore
import com.ailivequiz.app.data.repository.QuizRepository
import kotlinx.coroutines.cancelChildren
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MultipartBody

class AppViewModel : ViewModel() {

    private val repository = QuizRepository()

    private val _userId = MutableStateFlow<Int?>(null)
    val userId: StateFlow<Int?> = _userId.asStateFlow()

    // The name shown in the Library greeting: the username chosen at signup.
    private val _username = MutableStateFlow<String?>(null)
    val username: StateFlow<String?> = _username.asStateFlow()

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

    private val _recommendation = MutableStateFlow<RecommendationOut?>(null)
    val recommendation: StateFlow<RecommendationOut?> = _recommendation.asStateFlow()

    // Separate from the main isLoading flag: fetching a recommendation is a
    // deliberate button tap (it costs an AI call), not something that should
    // trigger the whole screen's loading spinner.
    private val _isLoadingRecommendation = MutableStateFlow(false)
    val isLoadingRecommendation: StateFlow<Boolean> = _isLoadingRecommendation.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    // questionId -> selectedOptionIndex, cleared whenever a new quiz starts
    private val _selectedAnswers = MutableStateFlow<Map<Int, Int>>(emptyMap())
    val selectedAnswers: StateFlow<Map<Int, Int>> = _selectedAnswers.asStateFlow()

    init {
        // Will be populated when user logs in via LoginScreen
    }

    /** Username from signup, or the first part of the email if none was ever set. */
    private fun displayNameFor(user: UserResponse): String =
        user.username?.takeIf { it.isNotBlank() } ?: user.email.substringBefore("@")

    fun loginUser(email: String, password: String, onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            repository.loginUser(email, password)
                .onSuccess {
                    _userId.value = it.id
                    _username.value = displayNameFor(it)
                    refreshDocuments()
                    onResult(true)
                }
                .onFailure {
                    _errorMessage.value = "Login failed: ${it.message}"
                    onResult(false)
                }
            _isLoading.value = false
        }
    }

    fun registerUser(username: String, email: String, password: String, onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            repository.registerUser(username, email, password)
                .onSuccess {
                    _userId.value = it.id
                    _username.value = displayNameFor(it)
                    refreshDocuments()
                    onResult(true)
                }
                .onFailure {
                    _errorMessage.value = "Registration failed: ${it.message}"
                    onResult(false)
                }
            _isLoading.value = false
        }
    }

    /**
     * Ends the session. Forgets the login token, cancels any request still in
     * flight (so a late response can't refill the screen after logout), and
     * wipes everything the previous user had loaded - so whoever logs in next
     * on this phone never sees it.
     */
    fun logout() {
        TokenStore.clear()
        viewModelScope.coroutineContext.cancelChildren()

        _userId.value = null
        _username.value = null
        _documents.value = emptyList()
        _currentQuiz.value = null
        _currentAttemptId.value = null
        _attemptResult.value = null
        _history.value = emptyList()
        _documentTopicStats.value = emptyList()
        _documentOverviewStats.value = null
        _recommendation.value = null
        _selectedAnswers.value = emptyMap()
        _isLoadingRecommendation.value = false
        _isLoading.value = false
        _errorMessage.value = null
    }

    fun refreshDocuments() {
        viewModelScope.launch {
            _isLoading.value = true
            repository.listDocuments()
                .onSuccess { _documents.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }

    fun uploadDocument(filePart: MultipartBody.Part, onDone: (DocumentResponse?) -> Unit) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.uploadDocument(filePart)
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
        viewModelScope.launch {
            _isLoading.value = true
            repository.startAttempt(quizId)
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
        viewModelScope.launch {
            _isLoading.value = true
            repository.getAttemptHistory()
                .onSuccess { _history.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }

    /** Loads topic breakdown + overview scoped to one document, for the per-PDF Insights screen. */
    fun refreshDocumentInsights(documentId: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _documentTopicStats.value = emptyList()
            _documentOverviewStats.value = null
            _recommendation.value = null // avoid showing a stale tip from a different document
            repository.getTopicStats(documentId)
                .onSuccess { _documentTopicStats.value = it }
                .onFailure { _errorMessage.value = it.message }
            repository.getOverview(documentId)
                .onSuccess { _documentOverviewStats.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoading.value = false
        }
    }

    /** Fetches an AI-written study recommendation. Call only on an explicit user tap (costs an AI call). */
    fun loadRecommendation(documentId: Int) {
        viewModelScope.launch {
            _isLoadingRecommendation.value = true
            repository.getRecommendation(documentId)
                .onSuccess { _recommendation.value = it }
                .onFailure { _errorMessage.value = it.message }
            _isLoadingRecommendation.value = false
        }
    }
}
