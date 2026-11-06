import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import DashboardLayout from './components/layout/DashboardLayout'
import { LoadingState } from './components/common/States'
import { useAuth } from './context/AuthContext'
import Accounts from './pages/Accounts'
import AIAssistant from './pages/AIAssistant'
import Analytics from './pages/Analytics'
import Bills from './pages/Bills'
import Budgets from './pages/Budgets'
import Dashboard from './pages/Dashboard'
import Notifications from './pages/Notifications'
import SavingsGoals from './pages/SavingsGoals'
import Settings from './pages/Settings'
import Transactions from './pages/Transactions'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'

function ProtectedRoute({ children }) {
  const { user, initializing } = useAuth()
  const location = useLocation()
  if (initializing) return <LoadingState label="Restoring your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

function GuestRoute({ children }) {
  const { user, initializing } = useAuth()
  if (initializing) return <LoadingState label="Loading…" />
  if (user) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestRoute><Login /></GuestRoute>} />
      <Route path="/register" element={<GuestRoute><Register /></GuestRoute>} />
      <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="budgets" element={<Budgets />} />
        <Route path="bills" element={<Bills />} />
        <Route path="savings" element={<SavingsGoals />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="assistant" element={<AIAssistant />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
