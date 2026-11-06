"""Import every model so Base.metadata is complete (used by Alembic)."""
from app.models.account import Account
from app.models.ai_conversation import AIConversation, AIMessage
from app.models.bill import Bill
from app.models.budget import Budget
from app.models.category import Category
from app.models.financial_insight import FinancialInsight
from app.models.notification import Notification
from app.models.savings_goal import GoalContribution, SavingsGoal
from app.models.transaction import Transaction
from app.models.user import RefreshToken, User

__all__ = [
    "Account", "AIConversation", "AIMessage", "Bill", "Budget", "Category", "FinancialInsight",
    "Notification", "GoalContribution", "SavingsGoal", "Transaction", "RefreshToken", "User",
]
