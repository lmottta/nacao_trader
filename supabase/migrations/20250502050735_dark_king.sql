/*
  # Insert Initial Data

  1. Test Users
    - Create 5 test users with profiles
  
  2. Sample Assets
    - Insert mock assets from the frontend data
  
  3. Sample Signals
    - Generate initial trading signals
*/

-- Insert test users (passwords are 'password123')
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
VALUES
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acc', 'trader1@example.com', '$2a$10$RVX3xC3dFfF9V6s1vZ5K5eK8x5v5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5', now(), now(), now()),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acd', 'trader2@example.com', '$2a$10$RVX3xC3dFfF9V6s1vZ5K5eK8x5v5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5', now(), now(), now()),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161ace', 'trader3@example.com', '$2a$10$RVX3xC3dFfF9V6s1vZ5K5eK8x5v5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5', now(), now(), now()),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acf', 'trader4@example.com', '$2a$10$RVX3xC3dFfF9V6s1vZ5K5eK8x5v5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5', now(), now(), now()),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161ac0', 'trader5@example.com', '$2a$10$RVX3xC3dFfF9V6s1vZ5K5eK8x5v5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5Q5', now(), now(), now());

-- Insert user profiles
INSERT INTO public.profiles (id, username, avatar_url)
VALUES
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acc', 'TraderPro', 'https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg'),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acd', 'MarketMaster', 'https://images.pexels.com/photos/733872/pexels-photo-733872.jpeg'),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161ace', 'TradingNinja', 'https://images.pexels.com/photos/1516680/pexels-photo-1516680.jpeg'),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161acf', 'StockWhisperer', 'https://images.pexels.com/photos/1181686/pexels-photo-1181686.jpeg'),
  ('d0d4e39c-3d54-4d0b-8fb9-3a4a42161ac0', 'CryptoKing', 'https://images.pexels.com/photos/1681010/pexels-photo-1681010.jpeg');

-- Insert assets
INSERT INTO public.assets (ticker, name, type)
VALUES
  ('AAPL', 'Apple Inc.', 'stock'),
  ('MSFT', 'Microsoft Corporation', 'stock'),
  ('AMZN', 'Amazon.com Inc.', 'stock'),
  ('GOOGL', 'Alphabet Inc.', 'stock'),
  ('META', 'Meta Platforms Inc.', 'stock'),
  ('TSLA', 'Tesla Inc.', 'stock'),
  ('NVDA', 'NVIDIA Corporation', 'stock'),
  ('EUR/USD', 'Euro / US Dollar', 'forex'),
  ('GBP/USD', 'British Pound / US Dollar', 'forex'),
  ('USD/JPY', 'US Dollar / Japanese Yen', 'forex'),
  ('BTC/USD', 'Bitcoin / US Dollar', 'crypto'),
  ('ETH/USD', 'Ethereum / US Dollar', 'crypto'),
  ('XRP/USD', 'Ripple / US Dollar', 'crypto'),
  ('ADA/USD', 'Cardano / US Dollar', 'crypto'),
  ('SOL/USD', 'Solana / US Dollar', 'crypto');

-- Insert some sample signals
INSERT INTO public.signals (asset_id, direction, accuracy, generated_at, valid_until)
SELECT 
  id as asset_id,
  CASE WHEN random() > 0.5 THEN 'CALL' ELSE 'PUT' END as direction,
  65 + floor(random() * 30) as accuracy,
  now() as generated_at,
  now() + interval '1 day' as valid_until
FROM public.assets;

-- Add some favorite assets for test users
INSERT INTO public.user_favorites (user_id, asset_id)
SELECT 
  u.id as user_id,
  a.id as asset_id
FROM auth.users u
CROSS JOIN public.assets a
WHERE random() < 0.3
LIMIT 25;

-- Add some user signals
INSERT INTO public.user_signals (user_id, signal_id, result)
SELECT 
  u.id as user_id,
  s.id as signal_id,
  CASE WHEN random() > 0.5 THEN 'success' ELSE 'failure' END as result
FROM auth.users u
CROSS JOIN public.signals s
WHERE random() < 0.2
LIMIT 50;