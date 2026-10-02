@file:OptIn(ExperimentalMaterial3Api::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.data.model.AttemptHistoryItem
import com.ailivequiz.app.ui.components.QGBottomBar
import com.ailivequiz.app.ui.theme.ErrorRed
import com.ailivequiz.app.ui.theme.SuccessGreen
import com.ailivequiz.app.ui.viewmodel.AppViewModel

@Composable
fun HistoryScreen(
    viewModel: AppViewModel,
    onBack: () -> Unit
) {
    val history by viewModel.history.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()

    LaunchedEffect(Unit) { viewModel.refreshHistory() }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text("History") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        },
        bottomBar = {
            QGBottomBar(
                currentTab = "history",
                onLibraryClick = onBack,
                onHistoryClick = {}
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            Column(modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
                Text(
                    "Your Quiz Journey",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    "Track your progress and revisit past attempts",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            if (isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            if (history.isEmpty() && !isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "No quiz attempts yet.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                LazyColumn(contentPadding = PaddingValues(20.dp)) {
                    items(history.filter { it.is_completed }) { item ->
                        HistoryCard(item)
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun HistoryCard(item: AttemptHistoryItem) {
    val total = item.total_questions ?: 0
    val score = item.score ?: 0
    val percentage = if (total > 0) (score * 100 / total) else 0
    val ringColor = when {
        percentage >= 80 -> SuccessGreen
        percentage >= 50 -> MaterialTheme.colorScheme.primary
        else -> ErrorRed
    }

    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            MiniPercentRing(percentage = percentage, color = ringColor)
            Spacer(modifier = Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    item.document_filename ?: "Quiz ${item.quiz_number ?: ""}",
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1
                )
                Text(
                    "$total questions",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    formatDate(item.completed_at),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun MiniPercentRing(percentage: Int, color: androidx.compose.ui.graphics.Color) {
    Box(
        modifier = Modifier.size(52.dp),
        contentAlignment = Alignment.Center
    ) {
        CircularProgressIndicator(
            progress = { 1f },
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.secondary,
            trackColor = MaterialTheme.colorScheme.secondary,
            strokeWidth = 5.dp
        )
        CircularProgressIndicator(
            progress = { (percentage / 100f).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxSize(),
            color = color,
            trackColor = androidx.compose.ui.graphics.Color.Transparent,
            strokeWidth = 5.dp
        )
        Text("$percentage%", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, fontSize = 11.sp)
    }
}

private val MONTH_NAMES = listOf(
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
)

private fun formatDate(iso: String?): String {
    if (iso.isNullOrBlank()) return "Not completed yet"
    return try {
        val datePart = iso.substringBefore("T")
        val parts = datePart.split("-")
        val year = parts[0]
        val month = MONTH_NAMES[parts[1].toInt() - 1]
        val day = parts[2].toInt()
        "$month $day, $year"
    } catch (e: Exception) {
        iso
    }
}
