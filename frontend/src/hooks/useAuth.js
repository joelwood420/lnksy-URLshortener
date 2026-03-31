import { useSessionCheck } from './useSessionCheck'
import { logout } from '../api'

export function useAuth(setShowMyUrls, setShowLogin) {
    const { currentUser, setCurrentUser } = useSessionCheck()

    const handleLoginSuccess = (email) => {
        setCurrentUser(email)
        setShowLogin(false)
        if (setShowMyUrls) {
            setShowMyUrls(prev => {
                if (prev) {
                    setTimeout(() => setShowMyUrls(true), 100)
                    return false
                }
                return prev
            })
        }
    }

    const handleLogout = async () => {
        try {
            await logout()
            setCurrentUser(null)
            setShowMyUrls(false)
        } catch (error) {
            console.error('Logout error:', error)
        }
    }

    return { currentUser, handleLoginSuccess, handleLogout }
}
