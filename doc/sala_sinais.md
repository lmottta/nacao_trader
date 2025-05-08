# Sala de Sinais: Modos de Visualização e Progressive Disclosure

Este documento descreve a implementação e os conceitos por trás dos novos modos de visualização da Sala de Sinais do Nação Trader.

## Visão Geral

A Sala de Sinais foi redesenhada para oferecer uma experiência de usuário superior, seguindo o princípio de "progressive disclosure" (revelação progressiva) para apresentar informações em camadas de complexidade crescente.

Os três modos de visualização permitem que o usuário escolha o nível de detalhe adequado às suas necessidades:

1. **Modo Compacto:** Visualização rápida com informações essenciais
2. **Modo Detalhado:** Visualização intermediária com mais contexto
3. **Modo Lista:** Visualização completa em formato tabular para análise detalhada

## Detalhamento dos Modos

### Modo Compacto

![Modo Compacto (Conceitual)](../public/assets/docs/modo-compacto-conceitual.png)

**Características:**
- Cards pequenos (4 por linha em desktop, 2 em tablet, 1 em mobile)
- Exibe apenas:
  - Símbolo do ativo (ex: "PETR4")
  - Direção recomendada (CALL/PUT) com cor indicativa (verde/vermelho)
  - Preço recomendado (ex: "R$ 35,42")
- Clique em qualquer card abre um modal com todos os detalhes

**Benefícios:**
- Visualização rápida de muitos sinais simultaneamente
- Identificação imediata de oportunidades por cor e direção
- Ideal para scanners rápidos de mercado
- Economiza espaço de tela em dispositivos móveis

**Implementação:**
```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
  {signals.map((signal) => (
    <div 
      key={signal.id}
      className="bg-gray-800 rounded-lg p-3 cursor-pointer hover:bg-gray-700 transition-all"
      onClick={() => openSignalModal(signal)}
    >
      <div className="flex justify-between items-center">
        <span className="text-lg font-bold">{signal.asset_symbol}</span>
        <Badge 
          color={signal.direction === 'CALL' ? 'green' : 'red'}
          className="text-xs font-bold"
        >
          {signal.direction}
        </Badge>
      </div>
      <div className="mt-2 text-sm text-gray-300">
        Preço: {formatCurrency(signal.recommended_price)}
      </div>
    </div>
  ))}
</div>
```

### Modo Detalhado

![Modo Detalhado (Conceitual)](../public/assets/docs/modo-detalhado-conceitual.png)

**Características:**
- Cards médios (3 por linha em desktop, 2 em tablet, 1 em mobile)
- Exibe:
  - Símbolo e nome do ativo
  - Direção recomendada com badges coloridos
  - Preço recomendado
  - Data/hora de geração e validade
  - Tipo de ativo (Ação, Forex, Cripto)
  - Status do mercado (Aberto, Fechado)
  - Botões de ação (Favoritar, Operar)

**Benefícios:**
- Equilíbrio entre informação e espaço
- Visão de contexto sem sobrecarregar
- Layout familiar, baseado no design anterior

**Implementação:**
```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
  {signals.map((signal) => (
    <SignalCard 
      key={signal.id}
      signal={signal}
      asset={findAssetForSignal(signal)}
      onToggleFavorite={handleToggleFavorite}
      onOperateClick={handleOperateClick}
    />
  ))}
</div>
```

### Modo Lista

![Modo Lista (Conceitual)](../public/assets/docs/modo-lista-conceitual.png)

**Características:**
- Formato tabular com colunas para todos os atributos
- 15 itens por página com paginação
- Colunas:
  - Símbolo/Nome
  - Direção
  - Preço Recomendado
  - Gerado em
  - Válido até
  - Tipo
  - Status
  - Confiança
  - Ações

**Benefícios:**
- Visualização densa de informações para análise comparativa
- Ordenação por colunas para diferentes perspectivas
- Ideal para traders profissionais que preferem visualização tabular
- Permite exportação para CSV com todos os dados

**Implementação:**
```tsx
<div className="overflow-x-auto">
  <table className="min-w-full bg-gray-800 text-white">
    <thead>
      <tr className="bg-gray-700 text-left">
        <th className="px-4 py-2">Ativo</th>
        <th className="px-4 py-2">Direção</th>
        <th className="px-4 py-2">Preço</th>
        <th className="px-4 py-2">Gerado</th>
        <th className="px-4 py-2">Validade</th>
        <th className="px-4 py-2">Tipo</th>
        <th className="px-4 py-2">Status</th>
        <th className="px-4 py-2">Confiança</th>
        <th className="px-4 py-2">Ações</th>
      </tr>
    </thead>
    <tbody>
      {pagedSignals.map((signal) => (
        <SignalRow 
          key={signal.id}
          signal={signal}
          asset={findAssetForSignal(signal)}
          onToggleFavorite={handleToggleFavorite}
          onOperateClick={handleOperateClick}
        />
      ))}
    </tbody>
  </table>
  <Pagination 
    currentPage={currentPage}
    totalPages={totalPages}
    onPageChange={setCurrentPage}
  />
</div>
```

## Modal de Detalhes

![Modal de Detalhes (Conceitual)](../public/assets/docs/modal-detalhes-conceitual.png)

O Modal de Detalhes é aberto ao clicar em um card no Modo Compacto, apresentando todas as informações do sinal:

**Características:**
- Layout em duas colunas para informações detalhadas
- Gráfico miniatura do ativo (quando disponível)
- Todas as informações do sinal, incluindo:
  - Detalhes do ativo (símbolo, nome, tipo)
  - Detalhes do sinal (direção, preço, confiança)
  - Timestamps (geração, validade)
  - Status do mercado
  - Razões técnicas para o sinal
  - Indicadores utilizados
  - Níveis de suporte e resistência
- Botões de ação (Favoritar, Registrar Operação)

**Implementação:**
```tsx
<Modal
  isOpen={isOpen}
  onClose={onClose}
  title={`Detalhes do Sinal: ${signal.asset_symbol}`}
  size="lg"
>
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div className="space-y-4">
      <div className="bg-gray-700 p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">Detalhes do Ativo</h3>
        <InfoRow label="Símbolo" value={signal.asset_symbol} />
        <InfoRow label="Nome" value={asset?.name || 'N/A'} />
        <InfoRow label="Tipo" value={getAssetTypeName(asset?.type)} />
        <InfoRow label="Status" value={getMarketStatusName(asset?.market_status)} />
      </div>
      
      <div className="bg-gray-700 p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">Detalhes do Sinal</h3>
        <InfoRow 
          label="Direção" 
          value={<Badge color={signal.direction === 'CALL' ? 'green' : 'red'}>{signal.direction}</Badge>} 
        />
        <InfoRow label="Preço Recomendado" value={formatCurrency(signal.recommended_price)} />
        <InfoRow label="Confiança" value={`${(signal.confidence * 100).toFixed(1)}%`} />
        <InfoRow label="Gerado em" value={formatDateTime(signal.generated_at)} />
        <InfoRow label="Válido até" value={formatDateTime(signal.valid_until)} />
      </div>
    </div>
    
    <div className="space-y-4">
      {asset?.thumbnail_url && (
        <img 
          src={asset.thumbnail_url} 
          alt={`Gráfico ${signal.asset_symbol}`}
          className="w-full rounded-lg"
        />
      )}
      
      <div className="bg-gray-700 p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">Análise Técnica</h3>
        <p className="text-sm text-gray-300 mb-3">{signal.technical_insight || 'Análise não disponível'}</p>
        
        {signal.indicators && (
          <>
            <h4 className="font-medium mb-1">Indicadores</h4>
            <ul className="text-sm text-gray-300 list-disc pl-5 mb-3">
              {Object.entries(signal.indicators).map(([key, value]) => (
                <li key={key}>{`${key}: ${value}`}</li>
              ))}
            </ul>
          </>
        )}
        
        {(signal.support_levels?.length > 0 || signal.resistance_levels?.length > 0) && (
          <>
            <h4 className="font-medium mb-1">Níveis Chave</h4>
            {signal.support_levels?.length > 0 && (
              <InfoRow label="Suportes" value={signal.support_levels.join(', ')} />
            )}
            {signal.resistance_levels?.length > 0 && (
              <InfoRow label="Resistências" value={signal.resistance_levels.join(', ')} />
            )}
          </>
        )}
      </div>
    </div>
  </div>
  
  <div className="flex justify-end mt-6 space-x-3">
    <Button 
      variant="outline"
      onClick={() => handleToggleFavorite(signal.asset_symbol)}
      leftIcon={isFavorite ? <StarFilledIcon /> : <StarIcon />}
    >
      {isFavorite ? 'Remover dos Favoritos' : 'Adicionar aos Favoritos'}
    </Button>
    <Button 
      variant="primary"
      onClick={() => handleOperateClick(signal)}
    >
      Registrar Operação
    </Button>
  </div>
</Modal>
```

## Controles de Interface

![Controles de Interface (Conceitual)](../public/assets/docs/controles-conceitual.png)

**Implementação:**
```tsx
<div className="flex flex-wrap justify-between items-center mb-6">
  <div className="flex items-center space-x-4 mb-4 md:mb-0">
    <h2 className="text-xl font-bold">Sala de Sinais</h2>
    <span className="text-sm text-gray-400">
      {filteredSignals.length} de {signals.length} sinais
    </span>
  </div>
  
  <div className="flex flex-wrap items-center gap-3">
    <div className="flex flex-wrap gap-2 mr-2">
      <button
        className={`px-3 py-1 rounded-md text-sm ${
          viewMode === 'compact' 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
        onClick={() => setViewMode('compact')}
        title="Modo Compacto - Visualização simplificada"
      >
        <CompactViewIcon className="h-4 w-4" />
      </button>
      
      <button
        className={`px-3 py-1 rounded-md text-sm ${
          viewMode === 'detailed' 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
        onClick={() => setViewMode('detailed')}
        title="Modo Detalhado - Cards com mais informações"
      >
        <DetailedViewIcon className="h-4 w-4" />
      </button>
      
      <button
        className={`px-3 py-1 rounded-md text-sm ${
          viewMode === 'list' 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
        onClick={() => setViewMode('list')}
        title="Modo Lista - Visualização em tabela"
      >
        <ListViewIcon className="h-4 w-4" />
      </button>
    </div>
    
    <AssetTypeFilter 
      selectedType={selectedAssetType}
      onChange={setSelectedAssetType}
    />
    
    <button
      className="px-3 py-1 rounded-md text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
      onClick={handleExportCSV}
      title="Exportar sinais para CSV"
    >
      <DownloadIcon className="h-4 w-4" />
    </button>
  </div>
</div>
```

## Progressive Disclosure

A abordagem de "progressive disclosure" (revelação progressiva) é um princípio de design de interface que consiste em:

1. Exibir inicialmente apenas as informações e controles essenciais
2. Revelar informações e controles adicionais conforme o usuário demonstra interesse ou necessidade
3. Organizar a informação em camadas de complexidade crescente

Na implementação da Sala de Sinais, este princípio se manifesta como:

**Nível 1: Modo Compacto**
- Apenas informações cruciais para decisão inicial (símbolo, direção, preço)
- Interação mínima necessária para avaliação rápida

**Nível 2: Modo Detalhado**
- Informações de contexto adicional (datas, tipos, status)
- Ações básicas disponíveis diretamente

**Nível 3: Modal de Detalhes**
- Todas as informações disponíveis sobre o sinal
- Análise técnica completa
- Ações avançadas

**Nível 4: Modo Lista**
- Visão analítica completa de todos os sinais
- Capacidade de ordenação e exportação
- Visualização tabular para usuários avançados

## Considerações Técnicas

### Otimização de Performance

Para garantir performance adequada mesmo com muitos sinais, foram implementadas as seguintes otimizações:

1. **Paginação:** No modo lista, limitado a 15 itens por página
2. **Renderização Condicional:** Componentes específicos para cada modo de visualização
3. **Memorização:** Uso de React.memo e useCallback para prevenir re-renderizações desnecessárias
4. **Virtualização:** Para listas muito longas no modo compacto, implementação de virtualização para renderizar apenas os itens visíveis

### Persistência de Preferências

As preferências do usuário são salvas no localStorage:

```tsx
// Hook para gerenciar a persistência do modo de visualização
const useViewMode = () => {
  const [viewMode, setViewModeState] = useState<ViewMode>(() => {
    const saved = localStorage.getItem('signalViewMode');
    return (saved as ViewMode) || 'detailed';
  });
  
  const setViewMode = (mode: ViewMode) => {
    localStorage.setItem('signalViewMode', mode);
    setViewModeState(mode);
  };
  
  return [viewMode, setViewMode] as const;
};
```

### Animações e Transições

Para melhorar a experiência do usuário, foram implementadas transições suaves:

```css
/* Transição entre modos de visualização */
.signals-container {
  transition: all 0.3s ease-in-out;
}

/* Animação ao abrir o modal */
.modal-enter {
  opacity: 0;
  transform: scale(0.95);
}

.modal-enter-active {
  opacity: 1;
  transform: scale(1);
  transition: opacity 200ms, transform 200ms;
}

.modal-exit {
  opacity: 1;
  transform: scale(1);
}

.modal-exit-active {
  opacity: 0;
  transform: scale(0.95);
  transition: opacity 200ms, transform 200ms;
}
```

## Próximos Passos

1. **Integração com Notificações:**
   - Notificações push para novos sinais importantes
   - Alertas de expiração de sinais

2. **Filtros Avançados:**
   - Filtro por confiança (>70%, >90%)
   - Filtro por resultado histórico
   - Filtro por proximidade de níveis chave

3. **Análise Avançada:**
   - Gráficos interativos embutidos
   - Mais indicadores técnicos
   - Análise de correlação entre sinais

4. **Performance e Escalabilidade:**
   - Implementação de virtualização para listas muito grandes
   - Otimização de queries Supabase para carregar apenas dados necessários
   - Cache de dados estáticos

## Conclusão

A implementação dos múltiplos modos de visualização na Sala de Sinais representa um avanço significativo na usabilidade da plataforma Nação Trader. Seguindo o princípio de "progressive disclosure", a interface agora atende a diferentes necessidades de usuários:

- **Traders iniciantes:** Modo compacto simplificado e modal de detalhes explicativo
- **Traders intermediários:** Modo detalhado com informações balanceadas
- **Traders avançados:** Modo lista para análise tabular completa

Esta abordagem demonstra como princípios de design centrado no usuário podem ser aplicados para melhorar significativamente a eficiência e a experiência em aplicações de trading. 