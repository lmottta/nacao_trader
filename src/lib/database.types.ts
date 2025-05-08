export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number
          created_at: string
          username: string
          email: string
          avatar: string | null
          favorites: string[] | null
        }
        Insert: {
          id?: number
          created_at?: string
          username: string
          email: string
          avatar?: string | null
          favorites?: string[] | null
        }
        Update: {
          id?: number
          created_at?: string
          username?: string
          email?: string
          avatar?: string | null
          favorites?: string[] | null
        }
      }
      assets: {
        Row: {
          id: string
          name: string
          symbol: string
          type: string
          created_at: string
          current_price: number | null
          price_change_24h: number | null
          data: Json | null
        }
        Insert: {
          id: string
          name: string
          symbol: string
          type: string
          created_at?: string
          current_price?: number | null
          price_change_24h?: number | null
          data?: Json | null
        }
        Update: {
          id?: string
          name?: string
          symbol?: string
          type?: string
          created_at?: string
          current_price?: number | null
          price_change_24h?: number | null
          data?: Json | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
} 