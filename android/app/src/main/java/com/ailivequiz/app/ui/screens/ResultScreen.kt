@file:OptIn(ExperimentalMaterial3Api::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.data.model.AnswerReview
import com.ailivequiz.app.ui.components.QGOutlinedButton
import com.ailivequiz.app.ui.components.QGPrimaryButton
import com.ailivequiz.app.ui.theme.ErrorRed
import com.ailivequiz.app.ui.theme.SuccessGreen
import com.ailivequiz.app.ui.viewmodel.AppViewModel

@Composable
fun ResultScreen(
    viewModel: AppViewModel,
    onDone: () -> Unit
) {
    val result by viewModel.attemptResult.collectAsState()
    var showReview by remember { mutableStateOf(false) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text(if (showReview) "Review Answers" else "Quiz Result") },
                navigationIcon = {
                    if (showReview) {
                        TextButton(onClick = { showReview = false }) {
                            Text("‹", fontSize = 24.sp, color = MaterialTheme.colorScheme.onBackground)
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        val currentResult = result
        if (currentResult == null) {
            Box(
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text("No result to show.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Scaffold
        }

        if (showReview) {
            LazyColumn(
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize(),
                contentPadding = PaddingValues(20.dp)
            ) {
                itemsIndexed(currentResult.answers) { index, answer ->
                    AnswerReviewCard(index + 1, answer)
                    Spacer(modifier = Modifier.height(14.dp))
                }
            }
        } else {
            Column(
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize()
                    .padding(horizontal = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(8.dp))
                Text("✦", fontSize = 22.sp, color = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "Quiz Complete!",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Spacer(modifier = Modifier.height(24.dp))

                ScoreRing(percentage = currentResult.percentage)

                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    "${currentResult.score} / ${currentResult.total_questions}",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    scoreMessage(currentResult.percentage),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(24.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    StatBadge(
                        label = "Correct",
                        value = currentResult.score,
                        color = SuccessGreen,
                        modifier = Modifier.weight(1f)
                    )
                    StatBadge(
                        label = "Incorrect",
                        value = currentResult.total_questions - currentResult.score,
                        color = ErrorRed,
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.weight(1f))

                QGPrimaryButton(
                    text = "Review Answers",
                    onClick = { showReview = true },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(10.dp))
                QGOutlinedButton(
                    text = "Back to Library",
                    onClick = onDone,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(20.dp))
            }
        }
    }
}

private fun scoreMessage(percentage: Double): String = when {
    percentage >= 90 -> "Outstanding work!"
    percentage >= 70 -> "Great progress!"
    percentage >= 50 -> "Good effort, keep going."
    else -> "Review the material and try again."
}

@Composable
private fun ScoreRing(percentage: Double) {
    Box(
        modifier = Modifier.size(160.dp),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator(
            progress = { 1f },
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.secondary,
            trackColor = MaterialTheme.colorScheme.secondary,
            strokeWidth = 14.dp
        )
        CircularProgressIndicator(
            progress = { (percentage / 100.0).toFloat().coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.primary,
            trackColor = androidx.compose.ui.graphics.Color.Transparent,
            strokeWidth = 14.dp
        )
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                "${percentage.toInt()}%",
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.onBackground
            )
        }
    }
}

@Composable
private fun StatBadge(label: String, value: Int, color: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier) {
    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.padding(vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(4.dp))
            Text(value.toString(), style = MaterialTheme.typography.headlineSmall, color = color, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun AnswerReviewCard(number: Int, answer: AnswerReview) {
    val accentColor = if (answer.is_correct) SuccessGreen else ErrorRed
    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "Question $number",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                answer.question_text,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(accentColor.copy(alpha = 0.12f))
                    .padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = if (answer.is_correct) Icons.Filled.Check else Icons.Filled.Close,
                    contentDescription = null,
                    tint = accentColor,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        "Your answer",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (!answer.explanation.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    "Explanation",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    answer.explanation,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        }
    }
}
