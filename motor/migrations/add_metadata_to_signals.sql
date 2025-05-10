-- Migração para adicionar coluna metadata à tabela signals
-- Verifica se a coluna já existe antes de criá-la

DO $$ 
BEGIN
    -- Verificar se a coluna metadata já existe
    IF NOT EXISTS (
        SELECT FROM pg_attribute 
        WHERE attrelid = 'signals'::regclass 
        AND attname = 'metadata'
        AND NOT attisdropped
    ) THEN
        -- Adicionar coluna metadata como JSONB
        ALTER TABLE signals 
        ADD COLUMN metadata JSONB;
        
        -- Comentário explicativo
        COMMENT ON COLUMN signals.metadata IS 'Dados adicionais do sinal como horários de entrada recomendados, preço alvo, stop loss, etc.';
        
        RAISE NOTICE 'Coluna metadata adicionada à tabela signals';
    ELSE
        RAISE NOTICE 'Coluna metadata já existe na tabela signals. Nenhuma alteração realizada.';
    END IF;
END $$; 