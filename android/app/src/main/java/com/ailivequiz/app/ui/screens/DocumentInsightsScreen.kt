@file:OptIn(ExperimentalMaterial3Api::class)

package com.ailivequiz.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ailivequiz.app.data.model.AttemptHistoryItem
import com.ailivequiz.app.data.model.OverviewStats
import com.ailivequiz.app.data.model.TopicStat
import com.ailivequiz.app.ui.theme.ErrorRed
import com.ailivequiz.app.ui.theme.SuccessGreen
import com.ailivequiz.app.ui.viewmodel.AppViewModel

@Composable
fun DocumentInsightsScreen(
    viewModel: AppViewModel,
    documentId: Int,
    onBack: () -> Unit
) {
    val documents by viewModel.documents.collectAsState()
    val document = documents.find { it.id == documentId }
    val overview by viewModel.documentOverviewStats.collectAsState()
    val topics by viewModel.documentTopicStats.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()

    LaunchedEffect(documentId) { viewModel.refreshDocumentInsights(documentId) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text("Insights") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("‹", fontSize = 24.sp, color = MaterialTheme.colorScheme.onBackground)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            if (isLoading && overview == null) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            val currentOverview = overview
            if (currentOverview == null || currentOverview.total_attempts == 0) {
                EmptyDocumentInsightsState(document?.filename)
            } else {
                LazyColumn(contentPadding = PaddingValues(20.dp)) {
                    item {
                        Text(
                            document?.filename ?: "This material",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        OverviewCardsRow(currentOverview)
                        ScoreTrendIndicator(currentOverview.recent_attempts)
                        Spacer(modifier = Modifier.height(16.dp))
                        RecommendationCard(viewModel = viewModel, documentId = documentId)
                        Spacer(modifier = Modifier.height(24.dp))
                        Text(
                            "Topic Breakdown",
                            style = MaterialTheme.typography.titleLarge,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                        Text(
                            "Weakest topics on this material first.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    if (topics.isEmpty()) {
                        item {
                            Text(
                                "No topic data yet.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    } else {
                        items(topics) { topic ->
                            DocumentTopicRow(topic)
                            Spacer(modifier = Modifier.height(10.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun OverviewCardsRow(overview: OverviewStats) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        StatCard(
            label = "Quizzes Taken",
            value = overview.total_attempts.toString(),
            modifier = Modifier.weight(1f)
        )
        StatCard(
            label = "Accuracy",
            value = "${overview.overall_accuracy_percentage.toInt()}%",
            modifier = Modifier.weight(1f)
        )
    }
}

/**
 * V4: compares the two most recent attempts on this document and shows
 * "up X% / down X% from previous attempt" - the "improvement rate" idea
 * from the proposal, using data we already have (no new instrumentation).
 */
@Composable
private fun ScoreTrendIndicator(recentAttempts: List<AttemptHistoryItem>) {
    if (recentAttempts.size < 2) return
    val latestPct = percentOf(recentAttempts[0]) ?: return
    val previousPct = percentOf(recentAttempts[1]) ?: return
    val diff = latestPct - previousPct
    if (diff == 0) return

    val isUp = diff > 0
    val color = if (isUp) SuccessGreen else ErrorRed
    val arrow = if (isUp) "↑" else "↓"

    Spacer(modifier = Modifier.height(8.dp))
    Text(
        "$arrow ${kotlin.math.abs(diff)}% from your previous attempt",
        style = MaterialTheme.typography.labelMedium,
        color = color,
        fontWeight = FontWeight.Bold
    )
}

private fun percentOf(item: AttemptHistoryItem): Int? {
    val total = item.total_questions ?: return null
    val score = item.score ?: return null
    if (total <= 0) return null
    return (score * 100) / total
}

/**
 * V4: AI-generated personalized study recommendation. Fetched only when the
 * person taps the button - not auto-loaded - since every tap is a real AI
 * API call.
 */
@Composable
private fun RecommendationCard(viewModel: AppViewModel, documentId: Int) {
    val recommendation by viewModel.recommendation.collectAsState()
    val isLoadingRec by viewModel.isLoadingRecommendation.collectAsState()
    val currentRecommendation = recommendation

    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("✦", fontSize = 18.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    "AI Study Tips",
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(8.dp))

            if (currentRecommendation != null) {
                Text(
                    currentRecommendation.recommendation,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
                Spacer(modifier = Modifier.height(10.dp))
                TextButton(
                    onClick = { viewModel.loadRecommendation(documentId) },
                    enabled = !isLoadingRec
                ) {
                    Text(
                        if (isLoadingRec) "Thinking..." else "Refresh tip",
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            } else {
                Text(
                    "Get a short, personalized study tip based on your weak topics.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.85f)
                )
                Spacer(modifier = Modifier.height(10.dp))
                Button(
                    onClick = { viewModel.loadRecommendation(documentId) },
                    enabled = !isLoadingRec,
                    shape = MaterialTheme.shapes.medium,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    )
                ) {
                    if (isLoadingRec) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            color = MaterialTheme.colorScheme.onPrimary,
                            strokeWidth = 2.dp
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Thinking...")
                    } else {
                        Text("Get Study Tips")
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(4.dp))
            Text(value, style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onBackground, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun DocumentTopicRow(topic: TopicStat) {
    val accentColor = if (topic.is_weak) ErrorRed else SuccessGreen

    Card(
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    topic.topic,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (topic.is_weak) {
                        Text(
                            "Weak",
                            style = MaterialTheme.typography.labelMedium,
                            color = ErrorRed,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(
                        "${topic.accuracy_percentage.toInt()}%",
                        style = MaterialTheme.typography.titleSmall,
                        color = accentColor,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { (topic.accuracy_percentage / 100.0).toFloat().coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(50)),
                color = accentColor,
                trackColor = MaterialTheme.colorScheme.outline
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                "${topic.correct} / ${topic.total_answered} correct",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun EmptyDocumentInsightsState(filename: String?) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("📊", style = MaterialTheme.typography.headlineLarge)
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                "No attempts yet",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                "Take a quiz on ${filename ?: "this material"} to see insights here.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
