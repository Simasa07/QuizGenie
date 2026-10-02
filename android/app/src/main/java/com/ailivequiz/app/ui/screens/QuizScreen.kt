@file:OptIn(ExperimentalMaterial3Api::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.data.model.OptionResponse
import com.ailivequiz.app.ui.components.QGPrimaryButton
import com.ailivequiz.app.ui.viewmodel.AppViewModel

private val OPTION_LETTERS = listOf("A", "B", "C", "D", "E", "F")

@Composable
fun QuizScreen(
    viewModel: AppViewModel,
    onSubmitted: () -> Unit
) {
    val quiz by viewModel.currentQuiz.collectAsState()
    val selectedAnswers by viewModel.selectedAnswers.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()

    val questions = quiz?.questions ?: emptyList()
    var currentIndex by remember(quiz?.id) { mutableIntStateOf(0) }

    if (questions.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    val currentQuestion = questions[currentIndex]
    val isLastQuestion = currentIndex == questions.lastIndex
    val selectedForCurrent = selectedAnswers[currentQuestion.id]
    val canProceed = selectedForCurrent != null

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text(quiz?.let { "Quiz ${it.quiz_number}" } ?: "Quiz") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        bottomBar = {
            Surface(color = MaterialTheme.colorScheme.background) {
                Column(modifier = Modifier.padding(20.dp)) {
                    errorMessage?.let {
                        Text(
                            it,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                    }
                    QGPrimaryButton(
                        text = when {
                            isLoading -> "Submitting..."
                            isLastQuestion -> "✓ Submit Quiz"
                            else -> "Next →"
                        },
                        enabled = canProceed,
                        loading = isLoading && isLastQuestion,
                        onClick = {
                            if (isLastQuestion) {
                                viewModel.submitAttempt { onSubmitted() }
                            } else {
                                currentIndex++
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "${currentIndex + 1} / ${questions.size}",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.align(Alignment.CenterHorizontally)
                    )
                }
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(horizontal = 20.dp)
        ) {
            Text(
                "Question ${currentIndex + 1} of ${questions.size}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { (currentIndex + 1f) / questions.size },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(50)),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.outline
            )
            Spacer(modifier = Modifier.height(20.dp))

            AnimatedContent(
                targetState = currentIndex,
                label = "question-transition",
                transitionSpec = { fadeIn() togetherWith fadeOut() }
            ) { _ ->
                Column {
                    QuestionPromptCard(currentQuestion.question_text)
                    Spacer(modifier = Modifier.height(20.dp))
                    currentQuestion.options.forEach { option ->
                        OptionRow(
                            letter = OPTION_LETTERS.getOrElse(option.option_index) { "?" },
                            option = option,
                            selected = selectedForCurrent == option.option_index,
                            onSelect = { viewModel.selectAnswer(currentQuestion.id, option.option_index) }
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun QuestionPromptCard(text: String) {
    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text,
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSecondaryContainer,
            modifier = Modifier.padding(18.dp)
        )
    }
}

@Composable
private fun OptionRow(
    letter: String,
    option: OptionResponse,
    selected: Boolean,
    onSelect: () -> Unit
) {
    val borderColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline
    val bgColor = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(bgColor)
            .border(1.5.dp, borderColor, MaterialTheme.shapes.medium)
            .clickable(onClick = onSelect)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(26.dp)
                .clip(CircleShape)
                .border(1.5.dp, if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline, CircleShape)
                .background(if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface),
            contentAlignment = Alignment.Center
        ) {
            if (selected) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.onPrimary)
                )
            }
        }
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            letter,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.width(10.dp))
        Text(
            option.option_text,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}
