/*
  # Initial Schema Setup for Nação Trader

  1. New Tables
    - `profiles`
      - `id` (uuid, references auth.users)
      - `username` (text)
      - `avatar_url` (text)
      - `created_at` (timestamp)
      - `updated_at` (timestamp)
    
    - `assets`
      - `id` (uuid)
      - `ticker` (text)
      - `name` (text)
      - `type` (text)
      - `created_at` (timestamp)
    
    - `signals`
      - `id` (uuid)
      - `asset_id` (uuid, references assets)
      - `direction` (text)
      - `accuracy` (numeric)
      - `generated_at` (timestamp)
      - `valid_until` (timestamp)
    
    - `user_favorites`
      - `id` (uuid)
      - `user_id` (uuid, references auth.users)
      - `asset_id` (uuid, references assets)
      - `created_at` (timestamp)
    
    - `user_signals`
      - `id` (uuid)
      - `user_id` (uuid, references auth.users)
      - `signal_id` (uuid, references signals)
      - `result` (text)
      - `entered_at` (timestamp)

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users
    - Restrict favorites to max 10 per user
*/

-- Create profiles table
CREATE TABLE public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  username text NOT NULL UNIQUE,
  avatar_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create assets table
CREATE TABLE public.assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker text NOT NULL UNIQUE,
  name text NOT NULL,
  type text NOT NULL CHECK (type IN ('stock', 'forex', 'crypto')),
  created_at timestamptz DEFAULT now()
);

-- Create signals table
CREATE TABLE public.signals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id uuid REFERENCES public.assets ON DELETE CASCADE NOT NULL,
  direction text NOT NULL CHECK (direction IN ('CALL', 'PUT')),
  accuracy numeric NOT NULL CHECK (accuracy >= 0 AND accuracy <= 100),
  generated_at timestamptz DEFAULT now(),
  valid_until timestamptz NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Create user_favorites table
CREATE TABLE public.user_favorites (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users ON DELETE CASCADE NOT NULL,
  asset_id uuid REFERENCES public.assets ON DELETE CASCADE NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, asset_id)
);

-- Create user_signals table
CREATE TABLE public.user_signals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users ON DELETE CASCADE NOT NULL,
  signal_id uuid REFERENCES public.signals ON DELETE CASCADE NOT NULL,
  result text CHECK (result IN ('success', 'failure')),
  entered_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_signals ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view all profiles"
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can update own profile"
  ON public.profiles
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id);

-- Assets policies
CREATE POLICY "Anyone can view assets"
  ON public.assets
  FOR SELECT
  TO authenticated
  USING (true);

-- Signals policies
CREATE POLICY "Anyone can view signals"
  ON public.signals
  FOR SELECT
  TO authenticated
  USING (true);

-- User favorites policies
CREATE POLICY "Users can view own favorites"
  ON public.user_favorites
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own favorites"
  ON public.user_favorites
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id);

-- User signals policies
CREATE POLICY "Users can view own signals"
  ON public.user_signals
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own signals"
  ON public.user_signals
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id);

-- Create function to enforce favorites limit
CREATE OR REPLACE FUNCTION check_favorites_limit()
RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT COUNT(*) FROM public.user_favorites WHERE user_id = NEW.user_id) >= 10 THEN
    RAISE EXCEPTION 'Users cannot have more than 10 favorites';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for favorites limit
CREATE TRIGGER check_favorites_limit_trigger
BEFORE INSERT ON public.user_favorites
FOR EACH ROW
EXECUTE FUNCTION check_favorites_limit();