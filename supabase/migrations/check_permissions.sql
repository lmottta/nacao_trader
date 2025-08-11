-- Verificar permissões das tabelas para os roles anon e authenticated
SELECT grantee, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND grantee IN ('anon', 'authenticated') 
ORDER BY table_name, grantee;

-- Conceder permissões básicas para o role anon (usuários não logados)
GRANT SELECT ON assets TO anon;
GRANT SELECT ON signals TO anon;
GRANT SELECT ON profiles TO anon;

-- Conceder permissões completas para o role authenticated (usuários logados)
GRANT ALL PRIVILEGES ON assets TO authenticated;
GRANT ALL PRIVILEGES ON signals TO authenticated;
GRANT ALL PRIVILEGES ON profiles TO authenticated;
GRANT ALL PRIVILEGES ON user_favorites TO authenticated;
GRANT ALL PRIVILEGES ON user_operations TO authenticated;
GRANT ALL PRIVILEGES ON user_signals TO authenticated;
GRANT ALL PRIVILEGES ON notifications TO authenticated;
GRANT ALL PRIVILEGES ON operation_results TO authenticated;
GRANT ALL PRIVILEGES ON leads TO authenticated;

-- Verificar novamente as permissões após a concessão
SELECT grantee, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND grantee IN ('anon', 'authenticated') 
ORDER BY table_name, grantee;