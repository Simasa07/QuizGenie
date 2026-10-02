package com.ailivequiz.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import com.ailivequiz.app.ui.screens.*
import com.ailivequiz.app.ui.viewmodel.AppViewModel

@Composable
fun AppNavGraph(viewModel: AppViewModel) {
    val navController: NavHostController = rememberNavController()

    NavHost(navController = navController, startDestination = Screen.Library.route) {

        composable(Screen.Library.route) {
            LibraryScreen(
                viewModel = viewModel,
                onDocumentSelected = { documentId ->
                    navController.navigate(Screen.QuizConfig.createRoute(documentId))
                },
                onHistoryClick = {
                    navController.navigate(Screen.History.route)
                }
            )
        }

        composable(
            route = Screen.QuizConfig.route,
            arguments = listOf(navArgument("documentId") { type = NavType.IntType })
        ) { backStackEntry ->
            val documentId = backStackEntry.arguments?.getInt("documentId") ?: return@composable
            QuizConfigScreen(
                viewModel = viewModel,
                documentId = documentId,
                onQuizReady = { quizId ->
                    viewModel.startAttempt(quizId) { attemptId ->
                        if (attemptId != null) {
                            navController.navigate(Screen.Quiz.route)
                        }
                    }
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(Screen.Quiz.route) {
            QuizScreen(
                viewModel = viewModel,
                onSubmitted = {
                    navController.navigate(Screen.Result.route) {
                        popUpTo(Screen.Library.route)
                    }
                }
            )
        }

        composable(Screen.Result.route) {
            ResultScreen(
                viewModel = viewModel,
                onDone = {
                    navController.navigate(Screen.Library.route) {
                        popUpTo(Screen.Library.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.History.route) {
            HistoryScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() }
            )
        }
    }
}
