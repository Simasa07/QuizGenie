@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.ui.components.GlyphBadge
import com.ailivequiz.app.ui.components.QGPrimaryButton
import com.ailivequiz.app.ui.viewmodel.AppViewModel

// The allowed ranges. These mirror the limits the backend enforces
// (QuizGenerateRequest: 1-30 questions, 1-120 minutes).
private const val MIN_QUESTIONS = 1
private const val MAX_QUESTIONS = 30
private const val MIN_MINUTES = 1
private const val MAX_MINUTES = 120

private data class DifficultyOption(val value: String, val label: String)
private val DIFFICULTY_OPTIONS = listOf(
    DifficultyOption("mixed", "Mixed"),
    DifficultyOption("easy", "Easy"),
    DifficultyOption("medium", "Medium"),
    DifficultyOption("hard", "Hard")
)

@Composable
fun QuizConfigScreen(
    viewModel: AppViewModel,
    documentId: Int,
    onQuizReady: (Int) -> Unit,
    onBack: () -> Unit
) {
    // The person types these in; we only show the allowed range.
    var questionsText by remember { mutableStateOf("") }
    var minutesText by remember { mutableStateOf("") }
    var difficulty by remember { mutableStateOf("mixed") }

    val numQuestions = questionsText.toIntOrNull()
    val timeLimitMinutes = minutesText.toIntOrNull()
    val questionsValid = numQuestions != null && numQuestions in MIN_QUESTIONS..MAX_QUESTIONS
    val minutesValid = timeLimitMinutes != null && timeLimitMinutes in MIN_MINUTES..MAX_MINUTES
    val isLoading by viewModel.isLoading.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val documents by viewModel.documents.collectAsState()
    val document = documents.find { it.id == documentId }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text("Quiz Setup") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("‹", fontSize = 24.sp, color = MaterialTheme.colorScheme.onBackground)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(8.dp))
            GlyphBadge(glyph = "📄", modifier = Modifier.size(64.dp))
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                document?.filename ?: "Study material",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(24.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outline)
            Spacer(modifier = Modifier.height(24.dp))

            // --- Question count ---
            SectionLabel(title = "How many questions?")
            Spacer(modifier = Modifier.height(10.dp))
            NumberField(
                value = questionsText,
                onValueChange = { questionsText = it },
                label = "Number of questions",
                placeholder = "e.g. 10",
                constraintText = "Between $MIN_QUESTIONS and $MAX_QUESTIONS questions",
                isError = questionsText.isNotEmpty() && !questionsValid
            )

            Spacer(modifier = Modifier.height(24.dp))

            // --- Time limit: a separate, independent choice from question count ---
            SectionLabel(title = "How much time?")
            Spacer(modifier = Modifier.height(10.dp))
            NumberField(
                value = minutesText,
                onValueChange = { minutesText = it },
                label = "Time limit (minutes)",
                placeholder = "e.g. 15",
                constraintText = "Between $MIN_MINUTES and $MAX_MINUTES minutes",
                isError = minutesText.isNotEmpty() && !minutesValid
            )

            Spacer(modifier = Modifier.height(24.dp))

            // --- Difficulty ---
            SectionLabel(title = "Difficulty")
            Spacer(modifier = Modifier.height(10.dp))
            FlowRowChips {
                DIFFICULTY_OPTIONS.forEach { option ->
                    SelectableChip(
                        label = option.label,
                        selected = difficulty == option.value,
                        onClick = { difficulty = option.value },
                        outlinedStyle = true
                    )
                }
            }

            Spacer(modifier = Modifier.height(20.dp))
            Card(
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("🧠", fontSize = 18.sp)
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        "AI will generate questions based on your document content.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            errorMessage?.let {
                Text(
                    it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
            }

            QGPrimaryButton(
                text = if (isLoading) "Generating..." else "✦  Generate Quiz",
                loading = isLoading,
                enabled = questionsValid && minutesValid,
                onClick = {
                    val questions = numQuestions
                    val minutes = timeLimitMinutes
                    if (questions != null && minutes != null) {
                        viewModel.generateQuiz(documentId, questions, difficulty, minutes) { quiz ->
                            if (quiz != null) onQuizReady(quiz.id)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "✦ Powered by AI",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(20.dp))
        }
    }
}

@Composable
private fun ColumnScope.SectionLabel(title: String, subtitle: String? = null) {
    Text(
        title,
        style = MaterialTheme.typography.titleMedium,
        color = MaterialTheme.colorScheme.onBackground,
        modifier = Modifier.align(Alignment.Start)
    )
    if (subtitle != null) {
        Text(
            subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.align(Alignment.Start)
        )
    }
}

/** Simple wrapping row: chips flow onto a second line instead of overflowing. */
@Composable
private fun FlowRowChips(content: @Composable () -> Unit) {
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        content()
    }
}

@Composable
private fun SelectableChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    outlinedStyle: Boolean = false
) {
    val bg = when {
        selected -> MaterialTheme.colorScheme.primary
        outlinedStyle -> MaterialTheme.colorScheme.surface
        else -> MaterialTheme.colorScheme.secondary
    }
    val fg = when {
        selected -> MaterialTheme.colorScheme.onPrimary
        outlinedStyle -> MaterialTheme.colorScheme.onSurface
        else -> MaterialTheme.colorScheme.onSecondary
    }
    val borderColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(14.dp))
            .background(bg)
            .border(1.dp, borderColor, RoundedCornerShape(14.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 12.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(label, style = MaterialTheme.typography.titleSmall, color = fg, fontWeight = FontWeight.Bold)
    }
}

/**
 * A numbers-only input that shows its allowed range underneath. The helper
 * line turns red when the typed value is outside that range.
 */
@Composable
private fun NumberField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String,
    constraintText: String,
    isError: Boolean
) {
    OutlinedTextField(
        value = value,
        onValueChange = { newValue ->
            // Digits only, and at most 3 characters (the largest allowed value is 120).
            if (newValue.length <= 3 && newValue.all { it.isDigit() }) onValueChange(newValue)
        },
        label = { Text(label) },
        placeholder = { Text(placeholder) },
        singleLine = true,
        isError = isError,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        supportingText = { Text(constraintText) },
        modifier = Modifier.fillMaxWidth()
    )
}
