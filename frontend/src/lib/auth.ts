// src/lib/auth.ts
// Simple auth system using localStorage (no backend needed for now)

export type User = {
  id: string;
  username: string;
  email: string;
  fullName: string;
  role: 'admin' | 'teacher' | 'student';
};

// Default users for testing
const DEFAULT_USERS: User[] = [
  {
    id: '1',
    username: 'admin',
    email: 'admin@college.edu',
    fullName: 'Admin User',
    role: 'admin'
  },
  {
    id: '2',
    username: 'teacher',
    email: 'teacher@college.edu',
    fullName: 'Prof. Sharma',
    role: 'teacher'
  },
  {
    id: '3',
    username: 'student',
    email: 'student@college.edu',
    fullName: 'John Doe',
    role: 'student'
  }
];

// Store current user
let currentUser: User | null = null;

// Login function
export const login = (username: string, password: string): { success: boolean; user?: User; error?: string } => {
  // Simple check - in real app, verify password too
  const user = DEFAULT_USERS.find(u => u.username === username);
  
  if (!user) {
    return { success: false, error: 'Invalid username' };
  }
  
  // For demo, any password works except empty
  if (!password) {
    return { success: false, error: 'Password required' };
  }
  
  currentUser = user;
  localStorage.setItem('currentUser', JSON.stringify(user));
  
  return { success: true, user };
};

// Logout function
export const logout = () => {
  currentUser = null;
  localStorage.removeItem('currentUser');
};

// Get current user
export const getCurrentUser = (): User | null => {
  if (currentUser) return currentUser;
  
  const stored = localStorage.getItem('currentUser');
  if (stored) {
    currentUser = JSON.parse(stored);
    return currentUser;
  }
  return null;
};

// Check if user is logged in
export const isAuthenticated = (): boolean => {
  return getCurrentUser() !== null;
};

// Check if user is admin
export const isAdmin = (): boolean => {
  const user = getCurrentUser();
  return user?.role === 'admin';
};

// Check if user is teacher
export const isTeacher = (): boolean => {
  const user = getCurrentUser();
  return user?.role === 'teacher';
};

// Check if user is student
export const isStudent = (): boolean => {
  const user = getCurrentUser();
  return user?.role === 'student';
};