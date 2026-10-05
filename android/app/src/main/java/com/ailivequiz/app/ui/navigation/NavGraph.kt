package com.ailivequiz.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.ailivequiz.app.ui.screens.*
import com.ailivequiz.app.ui.viewmodel.AppViewModel

@Composable
fun AppNavGraph(viewModel: AppViewModel) {
    val navController: NavHostController = rememberNavController()

    // Standard bottom-nav tab switching: avoids piling up Library -> History ->
    // Library -> History ... on the back stack. Whichever of the two root
    // tabs you're on, tapping the other always behaves the same way.
    fun navigateToTab(route: String) {
        navController.navigate(route) {
            popUpTo(Screen.Library.route) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    NavHost(navController = navController, startDestination = Screen.Library.route) {

        composable(Screen.Library.route) {
            LibraryScreen(
                viewModel = viewModel,
                onDocumentSelected = { documentId ->
                    navController.navigate(Screen.DocumentHub.createRoute(documentId))
                },
                onHistoryClick = { navigateToTab(Screen.History.route) }
            )
        }

        composable(
            route = Screen.DocumentHub.route,
            arguments = listOf(navArgument("documentId") { type = NavType.IntType })
        ) { backStackEntry ->
            val documentId = backStackEntry.arguments?.getInt("documentId") ?: return@composable
            DocumentHubScreen(
                viewModel = viewModel,
                documentId = documentId,
                onGenerateQuizClick = {
                    navController.navigate(Screen.QuizConfig.createRoute(documentId))
                },
                onInsightsClick = {
                    navController.navigate(Screen.DocumentInsights.createRoute(documentId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Screen.DocumentInsights.route,
            arguments = listOf(navArgument("documentId") { type = NavType.IntType })
        ) { backStackEntry ->
            val documentId = backStackEntry.arguments?.getInt("documentId") ?: return@composable
            DocumentInsightsScreen(
                viewModel = viewModel,
                documentId = documentId,
                onBack = { navController.popBackStack() }
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
                onBack = { navigateToTab(Screen.Library.route) },
                onAttemptClick = { attemptId ->
                    navController.navigate(Screen.ReviewResult.createRoute(attemptId))
                }
            )
        }

        composable(
            route = Screen.ReviewResult.route,
            arguments = listOf(navArgument("attemptId") { type = NavType.IntType })
        ) { backStackEntry ->
            val attemptId = backStackEntry.arguments?.getInt("attemptId") ?: return@composable
            LaunchedEffect(attemptId) {
                viewModel.loadAttemptResult(attemptId) {}
            }
            ResultScreen(
                viewModel = viewModel,
                // Came from History, not from finishing a live quiz, so just
                // pop back rather than routing through the Library stack reset.
                onDone = { navController.popBackStack() },
                doneLabel = "Back to History"
            )
        }
    }
}
