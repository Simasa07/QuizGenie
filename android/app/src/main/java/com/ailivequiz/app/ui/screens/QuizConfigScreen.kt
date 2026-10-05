@file:OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.ui.components.GlyphBadge
import com.ailivequiz.app.ui.components.QGPrimaryButton
import com.ailivequiz.app.ui.viewmodel.AppViewModel

private val PRESET_COUNTS = listOf(5, 10, 15, 20, 25, 30)
private val PRESET_MINUTES = listOf(5, 10, 15, 20, 30, 45)

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
    var numQuestions by remember { mutableIntStateOf(10) }
    var timeLimitMinutes by remember { mutableIntStateOf(10) }
    var difficulty by remember { mutableStateOf("mixed") }
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
            SectionLabel(title = "How many questions?", subtitle = "Choose between 1-30")
            Spacer(modifier = Modifier.height(14.dp))
            FlowRowChips {
                PRESET_COUNTS.forEach { count ->
                    SelectableChip(
                        label = count.toString(),
                        selected = numQuestions == count,
                        onClick = { numQuestions = count }
                    )
                }
            }
            Spacer(modifier = Modifier.height(10.dp))
            CustomStepper(
                label = "Custom:",
                value = numQuestions,
                onValueChange = { numQuestions = it.coerceIn(1, 30) }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // --- Time limit: a separate, independent choice from question count ---
            SectionLabel(title = "How much time?", subtitle = "Choose between 1-120 minutes")
            Spacer(modifier = Modifier.height(14.dp))
            FlowRowChips {
                PRESET_MINUTES.forEach { minutes ->
                    SelectableChip(
                        label = "${minutes}m",
                        selected = timeLimitMinutes == minutes,
                        onClick = { timeLimitMinutes = minutes }
                    )
                }
            }
            Spacer(modifier = Modifier.height(10.dp))
            CustomStepper(
                label = "Custom:",
                value = timeLimitMinutes,
                suffix = " min",
                onValueChange = { timeLimitMinutes = it.coerceIn(1, 120) }
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
                onClick = {
                    viewModel.generateQuiz(documentId, numQuestions, difficulty, timeLimitMinutes) { quiz ->
                        if (quiz != null) onQuizReady(quiz.id)
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

@Composable
private fun CustomStepper(
    label: String,
    value: Int,
    onValueChange: (Int) -> Unit,
    suffix: String = ""
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(10.dp))
        StepButton(symbol = "-", onClick = { onValueChange(value - 1) })
        Text(
            text = "$value$suffix",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        StepButton(symbol = "+", onClick = { onValueChange(value + 1) })
    }
}

@Composable
private fun StepButton(symbol: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(32.dp)
            .clip(RoundedCornerShape(10.dp))
            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(symbol, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
    }
}
