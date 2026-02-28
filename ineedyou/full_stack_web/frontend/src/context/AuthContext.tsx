import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

interface User {
  username: string;
  is_staff: boolean;
  email: string;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  isAdmin: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Token ${token}`;
        try {
          const res = await axios.get('http://localhost:8000/api/auth/me/');
          setUser(res.data);
        } catch (e) {
          console.error("Auth check failed", e);
          logout();
        }
      } else {
        delete axios.defaults.headers.common['Authorization'];
        setUser(null);
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const res = await axios.post('http://localhost:8000/api/auth/login/', { username, password });
      const newToken = res.data.token;
      localStorage.setItem('token', newToken);
      setToken(newToken);
      // user state will be updated by useEffect
      return true;
    } catch (e) {
      console.error("Login failed", e);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const value = {
    token,
    user,
    isAdmin: user?.is_staff || false,
    login,
    logout,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
