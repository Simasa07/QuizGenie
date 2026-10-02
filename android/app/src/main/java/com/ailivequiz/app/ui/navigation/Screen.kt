package com.ailivequiz.app.ui.navigation

sealed class Screen(val route: String) {
    data object Library : Screen("library")
    data object History : Screen("history")

    data object QuizConfig : Screen("quiz_config/{documentId}") {
        fun createRoute(documentId: Int) = "quiz_config/$documentId"
    }

    data object Quiz : Screen("quiz")
    data object Result : Screen("result")
}
