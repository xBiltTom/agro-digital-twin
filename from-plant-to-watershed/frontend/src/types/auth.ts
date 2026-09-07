export interface Permission {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions?: Permission[];
  created_at?: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  institution?: string | null;
  department?: string | null;
  scientific_specialty?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
  preferred_theme: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  roles: Role[];
  profile?: UserProfile | null;
  created_at: string;
  updated_at: string;
}

export interface UserBrief {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  avatar_url?: string | null;
  preferred_theme?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserBrief;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  institution?: string;
  scientific_specialty?: string;
}

export interface ProfileUpdatePayload {
  institution?: string;
  department?: string;
  scientific_specialty?: string;
  avatar_url?: string;
  bio?: string;
  preferred_theme?: string;
}

export interface PasswordChangePayload {
  old_password: string;
  new_password: string;
}
