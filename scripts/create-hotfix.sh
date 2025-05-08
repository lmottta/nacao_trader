#!/bin/bash
# Script para criar uma nova hotfix branch seguindo o GitFlow

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ $# -eq 0 ]; then
  echo -e "${RED}Erro: Nenhum nome de hotfix fornecido.${NC}"
  echo "Uso: $0 nome-do-hotfix"
  exit 1
fi

# Normaliza o nome do hotfix (minúsculas, traços em vez de espaços)
HOTFIX_NAME=$(echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
BRANCH_NAME="hotfix/$HOTFIX_NAME"

# Verifica se estamos em um repositório git
if [ ! -d .git ]; then
  echo -e "${RED}Erro: Não está em um repositório Git.${NC}"
  echo "Execute este script na raiz do projeto."
  exit 1
fi

# Verifica se a branch já existe
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
  echo -e "${RED}Erro: Branch '$BRANCH_NAME' já existe.${NC}"
  exit 1
fi

# Atualiza o repositório
echo -e "${YELLOW}Atualizando o repositório...${NC}"
git fetch --all

# Verifica se a branch main existe
if ! git show-ref --verify --quiet refs/heads/main; then
  echo -e "${RED}Erro: Branch 'main' não existe.${NC}"
  echo "Execute o script setup-gitflow.sh primeiro para configurar o GitFlow."
  exit 1
fi

# Cria a nova hotfix branch
echo -e "${YELLOW}Criando nova hotfix branch '$BRANCH_NAME' baseada em 'main'...${NC}"
git checkout main
git pull origin main
git checkout -b $BRANCH_NAME

# Cria arquivo de changelog para o hotfix
CHANGELOG_FILE="doc/hotfixes/$HOTFIX_NAME.md"
mkdir -p doc/hotfixes
cat > $CHANGELOG_FILE << EOF
# Hotfix: ${HOTFIX_NAME}

## Descrição do Problema
[Descreva o problema que este hotfix corrige]

## Causa Raiz
[Explique a causa raiz do problema]

## Solução Implementada
[Descreva a solução implementada]

## Arquivos Alterados
- Arquivo 1: Descrição da alteração
- Arquivo 2: Descrição da alteração

## Testes Realizados
- [ ] Teste 1
- [ ] Teste 2

## Verificação
- [ ] Correção aplicada em produção (main)
- [ ] Correção aplicada em homologação (staging)
- [ ] Correção aplicada em desenvolvimento (develop)

## Pull Request
- [ ] Criado em: [DATA]
- [ ] Revisado por: [REVISOR]
- [ ] Aprovado em: [DATA]
- [ ] Deployado em: [DATA]
EOF

# Adiciona o arquivo de changelog ao Git
git add $CHANGELOG_FILE
git commit -m "Inicia hotfix: $HOTFIX_NAME"

echo -e "\n${GREEN}Hotfix branch '$BRANCH_NAME' criada com sucesso!${NC}"
echo -e "Arquivo de changelog criado em: ${YELLOW}$CHANGELOG_FILE${NC}"
echo -e "\nPróximos passos:"
echo -e "1. Implemente a correção para o problema"
echo -e "2. Atualize o arquivo de changelog conforme necessário"
echo -e "3. Quando concluído, use: ${YELLOW}git checkout main && git merge $BRANCH_NAME${NC}"
echo -e "4. Não esqueça de aplicar a mesma correção para staging e develop:"
echo -e "   ${YELLOW}git checkout staging && git merge $BRANCH_NAME${NC}"
echo -e "   ${YELLOW}git checkout develop && git merge $BRANCH_NAME${NC}"
echo -e "5. Crie um Pull Request para revisão da correção" 