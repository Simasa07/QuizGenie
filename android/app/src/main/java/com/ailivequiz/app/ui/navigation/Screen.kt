package com.ailivequiz.app.ui.navigation

sealed class Screen(val route: String) {
    data object Library : Screen("library")
    data object History : Screen("history")

    data object DocumentHub : Screen("document_hub/{documentId}") {
        fun createRoute(documentId: Int) = "document_hub/$documentId"
    }

    data object DocumentInsights : Screen("document_insights/{documentId}") {
        fun createRoute(documentId: Int) = "document_insights/$documentId"
    }

    data object QuizConfig : Screen("quiz_config/{documentId}") {
        fun createRoute(documentId: Int) = "quiz_config/$documentId"
    }

    data object Quiz : Screen("quiz")
    data object Result : Screen("result")

    data object ReviewResult : Screen("review_result/{attemptId}") {
        fun createRoute(attemptId: Int) = "review_result/$attemptId"
    }
}
