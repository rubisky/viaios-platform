import { create } from 'zustand';

interface AppUser {
  id: string;
  username: string;
  role: string;
  tenantId: string;
}

interface AppState {
  user: AppUser | null;
  token: string | null;
  theme: 'dark' | 'light';
  setUser: (user: AppUser | null) => void;
  setToken: (token: string) => void;
  setTheme: (theme: 'dark' | 'light') => void;
  logout: () => void;
}

const savedToken = localStorage.getItem('viaios_token');
const savedTheme = (localStorage.getItem('viaios_theme') as 'dark' | 'light') || 'dark';

const useAppStore = create<AppState>((set) => ({
  user: null,
  token: savedToken,
  theme: savedTheme,

  setUser: (user) => set({ user }),
  setToken: (token) => {
    localStorage.setItem('viaios_token', token);
    set({ token });
  },
  setTheme: (theme) => {
    localStorage.setItem('viaios_theme', theme);
    set({ theme });
  },
  logout: () => {
    localStorage.removeItem('viaios_token');
    set({ user: null, token: null });
    window.location.href = '/login';
  },
}));

export default useAppStore;
